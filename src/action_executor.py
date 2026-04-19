"""
Action Executor — safely executes structured actions from the AI Brain.

Each action is a dict like ``{"type": "hotkey", "keys": ["ctrl", "c"]}``.
The executor maps these to pyautogui / pycaw / system calls.

Security: Only actions from the SYSTEM_PROMPT whitelist are accepted.
No arbitrary code execution.
"""

import os
import time
import webbrowser
import pyautogui
from threading import Thread
from logger import log


# ── Allowed action types (whitelist) ──────────────────────────────────────────
_ALLOWED_TYPES = {
    "click", "right_click", "double_click", "scroll",
    "hotkey", "press", "type_text",
    "open_app", "open_url", "search_google", "search_youtube",
    "volume", "brightness", "screenshot",
    "mode", "stop_all_modes", "mode_status",
    "lock_screen", "switch_window", "show_desktop",
    "minimize", "maximize", "close_window",
    "navigate_maps", "weather", "wikipedia",
    "sleep", "exit",
}

# Safe keys that can be pressed
_SAFE_KEYS = {
    "enter", "tab", "escape", "space", "delete", "backspace",
    "up", "down", "left", "right",
    "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12",
    "home", "end", "pageup", "pagedown", "insert",
}

# Safe modifier combos
_SAFE_MODIFIERS = {"ctrl", "alt", "shift", "win"}


def execute_actions(actions: list[dict], reply_fn, mode_hub_ref=None) -> str | None:
    """Execute a list of actions and return an override reply if needed.

    Parameters
    ----------
    actions : list of action dicts from AIBrain
    reply_fn : callable(text) to speak/display a message
    mode_hub_ref : tuple (hub, Mode) for mode switching

    Returns
    -------
    str or None — override reply text if the action produces one, else None
    """
    override_reply = None

    for action in actions:
        action_type = action.get("type", "")
        if action_type not in _ALLOWED_TYPES:
            log.warning("Action executor: unknown action type '%s' — skipping", action_type)
            continue

        try:
            result = _dispatch(action, reply_fn, mode_hub_ref)
            if result:
                override_reply = result
        except Exception as e:
            log.error("Action executor failed on %s: %s", action_type, e)

    return override_reply


def _dispatch(action: dict, reply_fn, mode_hub_ref) -> str | None:
    """Dispatch a single action. Returns override reply or None."""
    t = action["type"]

    if t == "click":
        pyautogui.click()

    elif t == "right_click":
        pyautogui.rightClick()

    elif t == "double_click":
        pyautogui.doubleClick()

    elif t == "scroll":
        direction = action.get("direction", "down")
        amount = int(action.get("amount", 5))
        pyautogui.scroll(amount if direction == "up" else -amount)

    elif t == "hotkey":
        keys = action.get("keys", [])
        # Validate keys
        safe_keys = []
        for k in keys:
            k_lower = k.lower()
            if k_lower in _SAFE_MODIFIERS or k_lower in _SAFE_KEYS or (len(k_lower) == 1 and k_lower.isalnum()):
                safe_keys.append(k_lower)
            else:
                log.warning("Action executor: blocked unsafe hotkey '%s'", k)
        if safe_keys:
            pyautogui.hotkey(*safe_keys)

    elif t == "press":
        key = action.get("key", "").lower()
        if key in _SAFE_KEYS or (len(key) == 1 and key.isalnum()):
            pyautogui.press(key)
        else:
            log.warning("Action executor: blocked unsafe key '%s'", key)

    elif t == "type_text":
        text = action.get("text", "")
        if text:
            time.sleep(0.3)
            pyautogui.write(text, interval=0.04)

    elif t == "open_app":
        name = action.get("name", "").strip()
        if name:
            # Map common names to Windows executables
            app_map = {
                "notepad": "notepad", "calculator": "calc", "calc": "calc",
                "paint": "mspaint", "ms paint": "mspaint",
                "file explorer": "explorer", "explorer": "explorer",
                "task manager": "taskmgr", "command prompt": "cmd",
                "cmd": "cmd", "powershell": "powershell",
                "word": "winword", "excel": "excel", "powerpoint": "powerpnt",
                "camera": "microsoft.windows.camera:",
                "settings": "ms-settings:",
                "snipping tool": "snippingtool",
            }
            cmd = app_map.get(name.lower(), name)
            os.system(f"start {cmd}")

    elif t == "open_url":
        url = action.get("url", "")
        if url and (url.startswith("http://") or url.startswith("https://")):
            webbrowser.get().open(url)
        else:
            log.warning("Action executor: blocked non-http URL '%s'", url)

    elif t == "search_google":
        query = action.get("query", "")
        if query:
            webbrowser.get().open(f"https://www.google.com/search?q={query.replace(' ', '+')}")

    elif t == "search_youtube":
        query = action.get("query", "")
        if query:
            webbrowser.get().open(f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}")

    elif t == "volume":
        _handle_volume(action.get("action", ""))

    elif t == "brightness":
        _handle_brightness(action.get("action", ""))

    elif t == "screenshot":
        pyautogui.hotkey("win", "prtsc")

    elif t == "mode":
        return _handle_mode(action, mode_hub_ref)

    elif t == "stop_all_modes":
        if mode_hub_ref:
            hub, Mode = mode_hub_ref
            for m in [Mode.EYE, Mode.GESTURE, Mode.KEYBOARD]:
                hub.stop(m)
            return "All input modes stopped"

    elif t == "mode_status":
        if mode_hub_ref:
            hub, Mode = mode_hub_ref
            active = hub.active_modes()
            if active:
                names = ", ".join(m.name.lower() for m in active)
                return f"Active modes: {names}"
            return "No input modes are currently active"

    elif t == "lock_screen":
        import ctypes
        ctypes.windll.user32.LockWorkStation()

    elif t == "switch_window":
        pyautogui.hotkey("alt", "tab")

    elif t == "show_desktop":
        pyautogui.hotkey("win", "d")

    elif t == "minimize":
        pyautogui.hotkey("win", "down")

    elif t == "maximize":
        pyautogui.hotkey("win", "up")

    elif t == "close_window":
        pyautogui.hotkey("alt", "f4")

    elif t == "navigate_maps":
        dest = action.get("destination", "")
        if dest:
            webbrowser.get().open(
                f"https://www.google.com/maps/dir/?api=1&destination={dest.replace(' ', '+')}")

    elif t == "weather":
        loc = action.get("location", "")
        q = f"weather+{loc.replace(' ', '+')}" if loc else "weather+today"
        webbrowser.get().open(f"https://www.google.com/search?q={q}")

    elif t == "wikipedia":
        topic = action.get("topic", "")
        if topic:
            try:
                import wikipedia as wiki
                result = wiki.summary(topic, sentences=2)
                return result
            except Exception:
                webbrowser.get().open(
                    f"https://en.wikipedia.org/wiki/{topic.replace(' ', '_')}")

    elif t == "sleep":
        pass  # Handled by caller (Proton.py sets is_awake = False)

    elif t == "exit":
        pass  # Handled by caller

    return None


def _handle_volume(action: str):
    """Adjust system volume."""
    from pycaw.pycaw import AudioUtilities
    try:
        try:
            vol = AudioUtilities.GetSpeakers().EndpointVolume
        except AttributeError:
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import IAudioEndpointVolume
            iface = AudioUtilities.GetSpeakers().Activate(
                IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            vol = cast(iface, POINTER(IAudioEndpointVolume))

        if action == "up":
            vol.SetMasterVolumeLevelScalar(
                min(vol.GetMasterVolumeLevelScalar() + 0.10, 1.0), None)
        elif action == "down":
            vol.SetMasterVolumeLevelScalar(
                max(vol.GetMasterVolumeLevelScalar() - 0.10, 0.0), None)
        elif action == "mute":
            vol.SetMute(1, None)
        elif action == "unmute":
            vol.SetMute(0, None)
    except Exception as e:
        log.error("Volume control failed: %s", e)


def _handle_brightness(action: str):
    """Adjust screen brightness."""
    try:
        import screen_brightness_control as sbc
        current = sbc.get_brightness(display=0)[0]
        if action == "up":
            sbc.set_brightness(min(current + 10, 100))
        elif action == "down":
            sbc.set_brightness(max(current - 10, 0))
    except Exception as e:
        log.error("Brightness control failed: %s", e)


def _handle_mode(action: dict, mode_hub_ref) -> str | None:
    """Start/stop/toggle an input mode."""
    if not mode_hub_ref:
        return "Mode control not available"

    hub, Mode = mode_hub_ref
    target = action.get("target", "").lower()
    op = action.get("action", "toggle").lower()

    mode_map = {
        "eye": Mode.EYE,
        "gesture": Mode.GESTURE,
        "keyboard": Mode.KEYBOARD,
    }

    mode = mode_map.get(target)
    if not mode:
        return f"Unknown mode: {target}"

    if op == "start":
        if hub.is_active(mode):
            return f"{target.capitalize()} control is already active"
        # Launch mode in daemon thread
        _launch_mode(mode, hub)
        return f"{target.capitalize()} control launched"
    elif op == "stop":
        if not hub.is_active(mode):
            return f"{target.capitalize()} control is already inactive"
        hub.stop(mode)
        if mode == Mode.GESTURE:
            try:
                from Gesture_Controller import GestureController
                GestureController.gc_mode = 0
            except Exception:
                pass
        return f"{target.capitalize()} control stopped"
    elif op == "toggle":
        was_active = hub.is_active(mode)
        if was_active:
            hub.stop(mode)
            if mode == Mode.GESTURE:
                try:
                    from Gesture_Controller import GestureController
                    GestureController.gc_mode = 0
                except Exception:
                    pass
            return f"{target.capitalize()} control stopped"
        else:
            _launch_mode(mode, hub)
            return f"{target.capitalize()} control launched"

    return None


def _launch_mode(mode, hub):
    """Launch a mode's function in a daemon thread."""
    from mode_hub import Mode
    if mode == Mode.EYE:
        from eye import eye_move
        Thread(target=eye_move, daemon=True).start()
    elif mode == Mode.GESTURE:
        from Gesture_Controller import gest_control
        Thread(target=gest_control, daemon=True).start()
    elif mode == Mode.KEYBOARD:
        from samvk import vk_keyboard
        Thread(target=vk_keyboard, daemon=True).start()
