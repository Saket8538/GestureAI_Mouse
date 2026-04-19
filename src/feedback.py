"""
Audio and visual feedback for mode switches and important events.

Plays a short beep and/or shows a Tkinter toast notification.
Thread-safe — can be called from any mode thread.
"""

import threading
from config_loader import get
from logger import log


def _beep(freq: int, duration: int):
    """Play a system beep (Windows only, silent fail on other OS)."""
    try:
        import winsound
        winsound.Beep(freq, duration)
    except Exception:
        pass


def play_start_sound():
    """Short rising beep for mode start."""
    if not get("feedback.sound_enabled", True):
        return
    freq = get("feedback.sound_frequency", 800)
    dur = get("feedback.sound_duration", 150)
    threading.Thread(target=_beep, args=(freq, dur), daemon=True).start()


def play_stop_sound():
    """Short falling beep for mode stop."""
    if not get("feedback.sound_enabled", True):
        return
    freq = get("feedback.sound_frequency_stop", 400)
    dur = get("feedback.sound_duration", 150)
    threading.Thread(target=_beep, args=(freq, dur), daemon=True).start()


def show_toast(message: str, duration: float = None):
    """Show a temporary floating notification window.

    Must be called from the main Tkinter thread OR uses its own root.
    Safe to call from any thread — creates its own Tk event loop if needed.
    """
    if not get("feedback.toast_enabled", True):
        return

    if duration is None:
        duration = get("feedback.toast_duration", 2.0)

    threading.Thread(
        target=_show_toast_impl,
        args=(message, duration),
        daemon=True,
    ).start()


def _show_toast_impl(message: str, duration: float):
    """Implementation: creates a small Toplevel toast that auto-fades."""
    try:
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        root.overrideredirect(True)

        # Position: bottom-right of screen
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        w, h = 320, 50
        x = sw - w - 20
        y = sh - h - 80
        root.geometry(f"{w}x{h}+{x}+{y}")
        root.deiconify()

        # Style
        frame = tk.Frame(root, bg="#2d3436", bd=0)
        frame.pack(fill="both", expand=True)
        tk.Label(
            frame,
            text=message,
            font=("Helvetica", 12, "bold"),
            fg="#dfe6e9",
            bg="#2d3436",
            padx=15,
            pady=10,
        ).pack(fill="both", expand=True)

        # Auto-close after duration
        root.after(int(duration * 1000), root.destroy)
        root.mainloop()
    except Exception as e:
        log.debug("Toast notification failed: %s", e)


def notify_mode_change(mode_name: str, started: bool):
    """Convenience: play sound + show toast for a mode change."""
    if started:
        play_start_sound()
        show_toast(f"▶  {mode_name} started")
    else:
        play_stop_sound()
        show_toast(f"■  {mode_name} stopped")
