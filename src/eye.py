import cv2
import mediapipe as mp
import pyautogui
import time
import math
import collections
from mode_hub import hub, Mode
from config_loader import get
from logger import log


def eye_move():
    """
    Eye-controlled mouse — accessibility edition.

    Blink detection uses consecutive-frame confirmation so natural flickers,
    half-blinks, and lighting changes are ignored.  Only a sustained blink
    held for BLINK_CONFIRM_FRAMES in a row triggers an action.

    Controls:
      Cursor       — look anywhere; iris centroid follows gaze (double-EMA smoothed)
      Left click   — quick blink (< 0.4 s)
      Right click  — slow blink (0.4–1.5 s)
      Double click — two quick blinks in succession (< 0.6 s gap)
      Drag/Select  — hold eyes closed > 1.5 s → mouseDown; open → mouseUp
      Dwell click  — keep gaze still 1.5 s → auto left-click (for non-blinkers)
      Scroll up    — look at top 10 % of screen (or raise eyebrows / tilt up)
      Scroll down  — look at bottom 10 % of screen (or tilt down)
      Quit         — press Q on the webcam window, or voice "stop eye control"
    """
    if hub.is_active(Mode.EYE):
        pass
    else:
        hub.start(Mode.EYE)
    log.info("Eye control starting...")

    def _cfg_float(path, default):
        """Read numeric config safely even if YAML value type is wrong."""
        try:
            return float(get(path, default))
        except (TypeError, ValueError):
            return float(default)

    def _cfg_int(path, default):
        """Read integer config safely even if YAML value type is wrong."""
        try:
            return int(get(path, default))
        except (TypeError, ValueError):
            return int(default)

    cam_idx = _cfg_int("eye.camera_index", 0)
    cam = cv2.VideoCapture(cam_idx)
    face_mesh = mp.solutions.face_mesh.FaceMesh(refine_landmarks=True)
    screen_w, screen_h = pyautogui.size()

    # ── Tuning constants (from config.yaml) ────────────────────────────────
    CLICK_COOLDOWN       = _cfg_float("eye.click_cooldown", 0.8)
    SCROLL_COOLDOWN      = _cfg_float("eye.scroll_cooldown", 0.25)
    LONG_BLINK_THRESHOLD = _cfg_float("eye.long_blink_threshold", 1.5)
    DWELL_THRESHOLD      = _cfg_float("eye.dwell_threshold", 1.5)
    DWELL_RADIUS         = _cfg_int("eye.dwell_radius", 35)
    EMA_ALPHA            = _cfg_float("eye.ema_alpha", 0.08)
    CALIB_FRAMES         = _cfg_int("eye.calib_frames", 60)
    GAZE_CALIB_FRAMES    = _cfg_int("eye.gaze_calib_frames", 120)
    BLINK_CONFIRM_FRAMES = _cfg_int("eye.blink_confirm_frames", 3)
    SHORT_BLINK_MAX      = _cfg_float("eye.short_blink_max", 0.4)
    DOUBLE_BLINK_WINDOW  = _cfg_float("eye.double_blink_window", 0.6)
    SCROLL_ZONE          = _cfg_float("eye.scroll_zone", 0.10)      # 10% edge zone
    SCROLL_AMOUNT        = _cfg_int("eye.scroll_amount", 3)
    DEADZONE             = _cfg_int("eye.deadzone", 5)               # pixel deadzone
    MEDIAN_WINDOW        = _cfg_int("eye.median_window", 5)          # frames for median pre-filter
    CURSOR_SPEED         = _cfg_float("eye.cursor_speed", 1.15)      # >1.0 moves a bit faster

    # ── EAR landmarks ──────────────────────────────────────────────────────
    LEFT_EYE_IDX  = [33, 160, 158, 133, 153, 144]
    RIGHT_EYE_IDX = [362, 385, 387, 263, 373, 380]

    def _ear(landmarks, eye_idx):
        """Eye Aspect Ratio: high when open, low when closed."""
        p = [landmarks[i] for i in eye_idx]
        v1 = math.hypot(p[1].x - p[5].x, p[1].y - p[5].y)
        v2 = math.hypot(p[2].x - p[4].x, p[2].y - p[4].y)
        h  = math.hypot(p[0].x - p[3].x, p[0].y - p[3].y)
        return (v1 + v2) / (2.0 * h + 1e-6)

    # ── State ──────────────────────────────────────────────────────────────
    smooth_x, smooth_y  = screen_w / 2, screen_h / 2
    smooth2_x, smooth2_y = screen_w / 2, screen_h / 2   # second EMA stage
    blink_start          = None
    last_short_blink_time = None
    pending_click_time   = None
    dragging             = False
    last_click_time     = 0.0
    last_scroll_time    = 0.0
    dwell_start         = None
    dwell_anchor_x      = None
    dwell_anchor_y      = None
    frame_count         = 0
    committed_x         = screen_w / 2   # persisted cursor pos (deadzone-aware)
    committed_y         = screen_h / 2
    first_detection     = True           # warp to first iris detection

    # Median pre-filter buffers (removes spike noise before EMA)
    iris_x_buf = collections.deque(maxlen=MEDIAN_WINDOW)
    iris_y_buf = collections.deque(maxlen=MEDIAN_WINDOW)

    # Blink threshold calibration
    calib_samples       = []
    blink_threshold     = 0.21
    calibrated          = False

    # Gaze range normalisation
    gaze_samples        = []
    iris_x_min, iris_x_max = 0.30, 0.70
    iris_y_min, iris_y_max = 0.30, 0.70
    gaze_calib_done     = False

    # Consecutive-frame blink counters (the "softener")
    left_closed_frames  = 0
    right_closed_frames = 0
    avg_closed_frames   = 0   # average-EAR based (more robust)

    # Head-tilt baseline for scroll (nose tip Y at rest)
    nose_y_baseline     = None
    nose_calib_samples  = []
    NOSE_TILT_THRESH    = 0.015   # normalised Y difference to trigger scroll

    try:
        while hub.is_active(Mode.EYE):
            ret, frame = cam.read()
            if not ret:
                break

            frame           = cv2.flip(frame, 1)
            rgb_frame       = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            output          = face_mesh.process(rgb_frame)
            landmark_points = output.multi_face_landmarks
            frame_h, frame_w, _ = frame.shape
            now             = time.time()
            frame_count    += 1
            status_text     = ''

            if landmark_points:
                landmarks = landmark_points[0].landmark

                # ── Nose tip baseline for head-tilt scroll ──────────────────────
                nose_y = landmarks[1].y   # nose tip
                if nose_y_baseline is None:
                    nose_calib_samples.append(nose_y)
                    if len(nose_calib_samples) >= 30:
                        nose_y_baseline = sum(nose_calib_samples) / len(nose_calib_samples)

                # ── Iris centroid: average of landmarks 474-477 ─────────────────
                iris_x = sum(landmarks[i].x for i in range(474, 478)) / 4.0
                iris_y = sum(landmarks[i].y for i in range(474, 478)) / 4.0

                for i in range(474, 478):
                    lm = landmarks[i]
                    cv2.circle(frame,
                               (int(lm.x * frame_w), int(lm.y * frame_h)),
                               3, (0, 255, 0), -1)

                # ── Gaze range auto-calibration (first GAZE_CALIB_FRAMES) ──────
                if not gaze_calib_done:
                    gaze_samples.append((iris_x, iris_y))
                    if len(gaze_samples) >= GAZE_CALIB_FRAMES:
                        xs = [s[0] for s in gaze_samples]
                        ys = [s[1] for s in gaze_samples]
                        margin = 0.06
                        iris_x_min = max(0.0, min(xs) - margin)
                        iris_x_max = min(1.0, max(xs) + margin)
                        iris_y_min = max(0.0, min(ys) - margin)
                        iris_y_max = min(1.0, max(ys) + margin)
                        gaze_calib_done = True

                # ── Median pre-filter (remove spike noise) ──────────────────────
                iris_x_buf.append(iris_x)
                iris_y_buf.append(iris_y)
                med_x = sorted(iris_x_buf)[len(iris_x_buf) // 2]
                med_y = sorted(iris_y_buf)[len(iris_y_buf) // 2]

                # ── Map iris to screen (normalised to detected range) ───────────
                norm_x = (med_x - iris_x_min) / max(iris_x_max - iris_x_min, 0.01)
                norm_y = (med_y - iris_y_min) / max(iris_y_max - iris_y_min, 0.01)
                norm_x = max(0.0, min(1.0, norm_x))
                norm_y = max(0.0, min(1.0, norm_y))
                raw_x  = norm_x * screen_w
                raw_y  = norm_y * screen_h

                # Scale speed from screen center so movement is faster but stable.
                if CURSOR_SPEED != 1.0:
                    cx, cy = screen_w / 2.0, screen_h / 2.0
                    raw_x = cx + (raw_x - cx) * CURSOR_SPEED
                    raw_y = cy + (raw_y - cy) * CURSOR_SPEED
                    raw_x = max(0.0, min(float(screen_w - 1), raw_x))
                    raw_y = max(0.0, min(float(screen_h - 1), raw_y))

                # ── Startup warp: jump to first detected position ───────────────
                if first_detection:
                    smooth_x = smooth2_x = committed_x = raw_x
                    smooth_y = smooth2_y = committed_y = raw_y
                    first_detection = False

                # ── Double-EMA smoothing (two cascaded stages) ──────────────────
                smooth_x = EMA_ALPHA * raw_x + (1.0 - EMA_ALPHA) * smooth_x
                smooth_y = EMA_ALPHA * raw_y + (1.0 - EMA_ALPHA) * smooth_y
                # Second EMA pass on the already-smoothed values
                EMA2 = min(EMA_ALPHA * 2.0, 1.0)   # faster second stage
                smooth2_x = EMA2 * smooth_x + (1.0 - EMA2) * smooth2_x
                smooth2_y = EMA2 * smooth_y + (1.0 - EMA2) * smooth2_y

                # ── Deadzone: ignore tiny jitter ────────────────────────────────
                dx = smooth2_x - committed_x
                dy = smooth2_y - committed_y
                move_dist = math.hypot(dx, dy)
                if move_dist > DEADZONE:
                    committed_x = smooth2_x
                    committed_y = smooth2_y

                pyautogui.moveTo(committed_x, committed_y)

                # ── EAR blink detection ─────────────────────────────────────────
                l_ear = _ear(landmarks, LEFT_EYE_IDX)
                r_ear = _ear(landmarks, RIGHT_EYE_IDX)

                if not calibrated and frame_count <= CALIB_FRAMES:
                    if l_ear > 0.15:
                        calib_samples.append(l_ear)
                    if len(calib_samples) >= CALIB_FRAMES // 2:
                        blink_threshold = sum(calib_samples) / len(calib_samples) * 0.72
                        calibrated = True

                # ── Consecutive-frame confirmation ──────────────────────────────
                raw_l_closed = l_ear < blink_threshold
                raw_r_closed = r_ear < blink_threshold

                if raw_l_closed:
                    left_closed_frames += 1
                else:
                    left_closed_frames = 0

                if raw_r_closed:
                    right_closed_frames += 1
                else:
                    right_closed_frames = 0

                # Use average EAR for blink detection — handles asymmetric
                # blinks (one eye closing slightly before the other) which
                # is extremely common and was causing missed clicks.
                avg_ear = (l_ear + r_ear) / 2.0
                if avg_ear < blink_threshold:
                    avg_closed_frames += 1
                else:
                    avg_closed_frames = 0

                both_closed = avg_closed_frames >= BLINK_CONFIRM_FRAMES

                # Visualise key eye landmarks
                for idx in LEFT_EYE_IDX + RIGHT_EYE_IDX:
                    pt = landmarks[idx]
                    cv2.circle(frame,
                               (int(pt.x * frame_w), int(pt.y * frame_h)),
                               2, (0, 255, 255), -1)

                # ── Duration-based blink actions ───────────────────────────────
                # Quick blink  < 0.4 s  → left click (delayed for double check)
                # Two quick blinks < 0.6 s gap → double click
                # Slow blink  0.4–1.5 s → right click
                # Long hold   > 1.5 s   → drag (mouseDown; mouseUp on open)

                if both_closed:
                    if blink_start is None:
                        blink_start = now
                    dwell_start = dwell_anchor_x = dwell_anchor_y = None
                    held = now - blink_start
                    if held > LONG_BLINK_THRESHOLD and not dragging:
                        pyautogui.mouseDown()
                        dragging = True
                    status_text = 'SELECTING...' if dragging else 'HOLDING...'

                else:
                    # Eyes open — resolve pending blink
                    if blink_start is not None:
                        held = now - blink_start
                        if dragging:
                            pyautogui.mouseUp()
                            dragging = False
                            status_text = 'RELEASED'
                        elif held < SHORT_BLINK_MAX:
                            if (last_short_blink_time is not None
                                    and now - last_short_blink_time < DOUBLE_BLINK_WINDOW):
                                pyautogui.doubleClick()
                                last_click_time = now
                                last_short_blink_time = None
                                pending_click_time = None
                                status_text = 'DOUBLE CLICK'
                            else:
                                last_short_blink_time = now
                                pending_click_time = now
                        elif held < LONG_BLINK_THRESHOLD:
                            if now - last_click_time > CLICK_COOLDOWN:
                                pyautogui.click(button='right')
                                last_click_time = now
                                status_text = 'RIGHT CLICK'
                            pending_click_time = None
                            last_short_blink_time = None
                        blink_start = None

                    # Fire delayed left click if no second blink came
                    if (pending_click_time is not None
                            and now - pending_click_time > DOUBLE_BLINK_WINDOW):
                        if now - last_click_time > CLICK_COOLDOWN:
                            pyautogui.click()
                            last_click_time = now
                            status_text = 'LEFT CLICK'
                        pending_click_time = None
                        last_short_blink_time = None

                    # ── Dwell-to-click ──────────────────────────────────────────
                    if not dragging and now - last_click_time > CLICK_COOLDOWN:
                        if dwell_anchor_x is None:
                            dwell_anchor_x = committed_x
                            dwell_anchor_y = committed_y
                            dwell_start    = now
                        else:
                            dist = math.hypot(committed_x - dwell_anchor_x,
                                              committed_y - dwell_anchor_y)
                            if dist > DWELL_RADIUS:
                                dwell_anchor_x = committed_x
                                dwell_anchor_y = committed_y
                                dwell_start    = now
                            else:
                                elapsed  = now - dwell_start
                                progress = min(elapsed / DWELL_THRESHOLD, 1.0)
                                cx = int(dwell_anchor_x / screen_w * frame_w)
                                cy = int(dwell_anchor_y / screen_h * frame_h)
                                cv2.circle(frame, (cx, cy), DWELL_RADIUS,
                                           (80, 80, 80), 1)
                                cv2.ellipse(frame, (cx, cy),
                                            (DWELL_RADIUS, DWELL_RADIUS),
                                            -90, 0, int(-360 * progress),
                                            (0, 200, 255), 3)
                                if progress >= 1.0:
                                    pyautogui.click()
                                    last_click_time = now
                                    dwell_start = dwell_anchor_x = dwell_anchor_y = None
                                    status_text = 'DWELL CLICK'
                                else:
                                    status_text = f'DWELL {int(progress * 100)}%'
                    else:
                        dwell_anchor_x = dwell_anchor_y = dwell_start = None

                # ── Scroll: gaze zone OR head tilt ──────────────────────────
                scroll_triggered = False

                # Method 1: Gaze at top/bottom SCROLL_ZONE of screen
                if committed_y < screen_h * SCROLL_ZONE:
                    if now - last_scroll_time > SCROLL_COOLDOWN:
                        pyautogui.scroll(SCROLL_AMOUNT)
                        last_scroll_time = now
                    cv2.putText(frame, 'SCROLL UP (gaze)', (30, 120),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
                    scroll_triggered = True
                elif committed_y > screen_h * (1.0 - SCROLL_ZONE):
                    if now - last_scroll_time > SCROLL_COOLDOWN:
                        pyautogui.scroll(-SCROLL_AMOUNT)
                        last_scroll_time = now
                    cv2.putText(frame, 'SCROLL DOWN (gaze)', (30, 120),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
                    scroll_triggered = True

                # Method 2: Head tilt (nose tip Y vs baseline)
                if not scroll_triggered and nose_y_baseline is not None:
                    tilt = nose_y - nose_y_baseline
                    if tilt < -NOSE_TILT_THRESH:     # head tilted UP
                        if now - last_scroll_time > SCROLL_COOLDOWN:
                            pyautogui.scroll(SCROLL_AMOUNT)
                            last_scroll_time = now
                        cv2.putText(frame, 'SCROLL UP (tilt)', (30, 120),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                    elif tilt > NOSE_TILT_THRESH:    # head tilted DOWN
                        if now - last_scroll_time > SCROLL_COOLDOWN:
                            pyautogui.scroll(-SCROLL_AMOUNT)
                            last_scroll_time = now
                        cv2.putText(frame, 'SCROLL DOWN (tilt)', (30, 120),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

            # ── Gaze calibration progress bar ──────────────────────────────────
            if not gaze_calib_done and frame_count <= GAZE_CALIB_FRAMES:
                pct = int(frame_count / GAZE_CALIB_FRAMES * 100)
                cv2.rectangle(frame, (0, frame_h - 20),
                              (int(frame_w * pct / 100), frame_h), (0, 180, 0), -1)
                cv2.putText(frame,
                            f'Calibrating... {pct}%  (slowly look at all screen corners)',
                            (8, frame_h - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                            (255, 255, 0), 1)

            # ── HUD bar ────────────────────────────────────────────────────────
            cv2.rectangle(frame, (0, 0), (frame_w, 42), (0, 0, 0), -1)
            hud = 'Blink=Click | SlowBlink=RClick | LongHold=Drag | Tilt=Scroll | Q=Quit'
            cv2.putText(frame, hud,
                        (8, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (200, 200, 200), 1)
            # Show live EAR so users can verify blink detection is working
            if landmark_points:
                ear_hud = f'EAR: {avg_ear:.2f} / thr: {blink_threshold:.2f}'
                cv2.putText(frame, ear_hud, (frame_w - 280, 28),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)

            if status_text:
                cv2.putText(frame, status_text, (30, 80),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            cv2.imshow('Eye Controlled Mouse', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        hub.stop(Mode.EYE)
        cam.release()
        cv2.destroyAllWindows()

