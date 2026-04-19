import cv2
from cvzone.HandTrackingModule import HandDetector
import time
from pynput.keyboard import Controller, Key
from mode_hub import hub, Mode
from config_loader import get
from logger import log


def vk_keyboard():
    """
    Hand-gesture virtual keyboard with soft debounce.

    Improvements:
      - Time-based debounce per key: same key won't fire again within 0.4 s
      - Must RELEASE pinch (fingers apart) before the same key can re-trigger
      - Added ENTER, TAB, CAPS special keys
      - Caps-lock visual indicator
      - Mode-hub integration: stops when hub says so, or press Q

    Controls:
      - Hover index fingertip (landmark 8) over a key to highlight it.
      - Pinch index + middle finger (distance < 30 px) to type the key.
      - SPACE   : types a space
      - BKSP    : deletes last character
      - ENTER   : presses Enter
      - TAB     : presses Tab
      - CAPS    : toggles caps lock
      - Press Q on the OpenCV window or say "stop keyboard" to quit.
    """
    if not hub.is_active(Mode.KEYBOARD):
        hub.start(Mode.KEYBOARD)
    log.info("Virtual keyboard starting...")

    cam_idx = get("keyboard.camera_index", 0)

    # Retry camera open — previous mode may still be releasing it
    cap = None
    for _attempt in range(10):
        cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW)
        if cap.isOpened():
            break
        cap.release()
        log.info("Keyboard: waiting for camera %d...", cam_idx)
        time.sleep(0.5)

    if cap is None or not cap.isOpened():
        log.error("Keyboard: could not open camera %d", cam_idx)
        hub.stop(Mode.KEYBOARD)
        return

    cap.set(3, 1280)
    cap.set(4, 720)
    detector = HandDetector(detectionCon=0.8)

    keyboard_keys = [
        ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
        ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
        ["A", "S", "D", "F", "G", "H", "J", "K", "L", ";"],
        ["Z", "X", "C", "V", "B", "N", "M", ",", ".", "/"],
    ]

    final_text = ""
    keyboard = Controller()
    caps_on = False

    # Debounce state
    KEY_COOLDOWN = get("keyboard.key_cooldown", 0.40)
    PINCH_DISTANCE = get("keyboard.pinch_distance", 30)
    last_press_time = {}      # {key_text: timestamp}
    pinch_was_active = False  # must release pinch before next key fires

    class Button1:
        def __init__(self, pos, text, size=(85, 85)):
            self.pos = pos
            self.size = size
            self.text = text

    def draw(img, buttonList, caps):
        for btn in buttonList:
            x, y = btn.pos
            w, h = btn.size
            # Caps indicator
            if btn.text == 'CAPS':
                color = (0, 200, 0) if caps else (255, 144, 30)
            else:
                color = (255, 144, 30)
            cv2.rectangle(img, (x, y), (x + w, y + h), color, cv2.FILLED)
            cv2.rectangle(img, (x, y), (x + w, y + h), (50, 50, 50), 2)
            font_scale = 4 if w <= 90 else 3
            cv2.putText(img, btn.text, (x + 15, y + 65),
                        cv2.FONT_HERSHEY_PLAIN, font_scale, (0, 0, 0), 4)
        return img

    # Build regular key buttons (rows 0-3)
    buttonList = []
    for row_idx, row in enumerate(keyboard_keys):
        for col_idx, key in enumerate(row):
            buttonList.append(Button1([100 * col_idx + 25, 100 * row_idx + 20], key))

    # Special keys row (below the 4 letter rows)
    buttonList.append(Button1([25,  430], 'SPACE', size=(350, 85)))
    buttonList.append(Button1([390, 430], 'BKSP',  size=(170, 85)))
    buttonList.append(Button1([575, 430], 'ENTER', size=(170, 85)))
    buttonList.append(Button1([760, 430], 'TAB',   size=(120, 85)))
    buttonList.append(Button1([895, 430], 'CAPS',  size=(120, 85)))

    try:
        while hub.is_active(Mode.KEYBOARD):
            success, img = cap.read()
            if not success:
                time.sleep(0.05)
                continue

            img = cv2.flip(img, 1)
            allHands, img = detector.findHands(img)
            img = draw(img, buttonList, caps_on)

            pinch_active_this_frame = False
            now = time.time()

            if allHands:
                lmList = allHands[0]["lmList"]
                for btn in buttonList:
                    x, y = btn.pos
                    w, h = btn.size

                    if x < lmList[8][0] < x + w and y < lmList[8][1] < y + h:
                        # Highlight (yellow)
                        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 255), cv2.FILLED)
                        cv2.rectangle(img, (x, y), (x + w, y + h), (50, 50, 50), 2)
                        font_scale = 4 if w <= 90 else 3
                        cv2.putText(img, btn.text, (x + 15, y + 65),
                                    cv2.FONT_HERSHEY_PLAIN, font_scale, (0, 0, 0), 4)

                        p1 = (lmList[8][0], lmList[8][1])
                        p2 = (lmList[12][0], lmList[12][1])
                        l, _, _ = detector.findDistance(p1, p2)
                        if l < PINCH_DISTANCE:
                            pinch_active_this_frame = True

                            # ── Debounce: must have released + cooldown passed ──
                            last_t = last_press_time.get(btn.text, 0.0)
                            if not pinch_was_active and (now - last_t) > KEY_COOLDOWN:
                                # Pressed (green flash)
                                cv2.rectangle(img, (x, y), (x + w, y + h),
                                              (0, 255, 0), cv2.FILLED)
                                cv2.rectangle(img, (x, y), (x + w, y + h),
                                              (50, 50, 50), 2)
                                cv2.putText(img, btn.text, (x + 15, y + 65),
                                            cv2.FONT_HERSHEY_PLAIN, font_scale,
                                            (0, 0, 0), 4)

                                last_press_time[btn.text] = now

                                if btn.text == 'SPACE':
                                    keyboard.press(' ')
                                    keyboard.release(' ')
                                    final_text += ' '
                                elif btn.text == 'BKSP':
                                    keyboard.press(Key.backspace)
                                    keyboard.release(Key.backspace)
                                    final_text = final_text[:-1] if final_text else ''
                                elif btn.text == 'ENTER':
                                    keyboard.press(Key.enter)
                                    keyboard.release(Key.enter)
                                    final_text += '\n'
                                elif btn.text == 'TAB':
                                    keyboard.press(Key.tab)
                                    keyboard.release(Key.tab)
                                    final_text += '\t'
                                elif btn.text == 'CAPS':
                                    caps_on = not caps_on
                                else:
                                    ch = btn.text.lower() if not caps_on else btn.text
                                    keyboard.press(ch)
                                    keyboard.release(ch)
                                    final_text += ch

            pinch_was_active = pinch_active_this_frame

            # Text display bar
            cv2.rectangle(img, (25, 530), (1050, 630), (255, 255, 255), cv2.FILLED)
            cv2.rectangle(img, (25, 530), (1050, 630), (0, 0, 0), 2)
            display = final_text.replace('\n', ' ').replace('\t', '  ')[-28:]
            cv2.putText(img, display, (40, 605),
                        cv2.FONT_HERSHEY_PLAIN, 3.5, (0, 0, 0), 3)

            # Caps indicator in corner
            if caps_on:
                cv2.putText(img, 'CAPS ON', (1100, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 0), 2)

            cv2.imshow("Virtual Keyboard", img)
            if cv2.waitKey(1) == 113:   # Q = quit
                break

    finally:
        hub.stop(Mode.KEYBOARD)
        cap.release()
        cv2.destroyAllWindows()
