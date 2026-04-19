import sys
import os

# ── Auto-activate virtual environment if not already active ───────────────────
# This lets the app run correctly even when launched without manually activating
# the .venv first (e.g. double-clicking main.py or running `python main.py`
# from a fresh terminal).
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_VENV_PYTHON = os.path.join(_ROOT, '.venv', 'Scripts', 'python.exe')
_VENV_SITE   = os.path.join(_ROOT, '.venv', 'Lib', 'site-packages')
if os.path.isdir(_VENV_SITE) and _VENV_SITE not in sys.path:
    sys.path.insert(0, _VENV_SITE)

import tkinter as tk
import tkinter.font as font
from threading import Thread
from Gesture_Controller import gest_control
from eye import eye_move
from samvk import vk_keyboard
from PIL import Image, ImageTk
from Proton import proton_chat
from mode_hub import hub, Mode
from logger import log

# Resolve paths relative to this file so it works from any working directory
_SRC_DIR  = os.path.dirname(os.path.abspath(__file__))
_ICONS_DIR = os.path.join(_SRC_DIR, '..', 'icons')

def _icon(name):
    return os.path.normpath(os.path.join(_ICONS_DIR, name))

def _load(name, size):
    img = Image.open(_icon(name))
    img = img.resize(size, Image.Resampling.LANCZOS)
    return ImageTk.PhotoImage(img)

# Mode → launcher function mapping
_MODE_FUNCS = {
    Mode.VOICE:    proton_chat,
    Mode.EYE:      eye_move,
    Mode.GESTURE:  gest_control,
    Mode.KEYBOARD: vk_keyboard,
}

def _stop_all_modes():
    """Stop every active mode — used by the Escape key."""
    for mode in Mode:
        if hub.is_active(mode):
            hub.stop(mode)
            log.info("Mode stopped via ESC: %s", mode.name)
            if mode == Mode.GESTURE:
                from Gesture_Controller import GestureController
                GestureController.gc_mode = 0

def _toggle_mode(mode):
    """Toggle a mode on/off.  If turning on, launch its function in a daemon thread."""
    if hub.is_active(mode):
        hub.stop(mode)
        log.info("Mode stopped via GUI: %s", mode.name)
        # Gesture controller also needs its legacy flag cleared
        if mode == Mode.GESTURE:
            from Gesture_Controller import GestureController
            GestureController.gc_mode = 0
    else:
        # Prevent double-start: mark active immediately so rapid clicks don't
        # spawn duplicate threads before the worker calls hub.start() itself.
        hub.start(mode)
        log.info("Mode started via GUI: %s", mode.name)
        Thread(target=_MODE_FUNCS[mode], daemon=True).start()

# ── Window ────────────────────────────────────────────────────────────────────
window = tk.Tk()
window.title("Gesture Controlled Virtual Mouse and Keyboard")
window.iconphoto(False, tk.PhotoImage(file=_icon('mn.png')))
window.geometry('1080x750')
window.resizable(False, False)
BG = '#f0f2f5'
window.configure(bg=BG)

# Centre window on screen
window.update_idletasks()
sx = (window.winfo_screenwidth()  - 1080) // 2
sy = (window.winfo_screenheight() - 750)  // 2
window.geometry(f'1080x750+{sx}+{sy}')

# ── Images (must stay referenced at module level to avoid GC) ─────────────────
img_man  = _load('man.jpeg',    (340, 265))
img_bot  = _load('bot.png',     (62, 62))
img_kbd  = _load('keyboard.png',(62, 62))
img_eye  = _load('eye.jpeg',    (72, 72))
img_hand = _load('hand.png',    (62, 62))
img_exit = _load('exit.png',    (52, 52))

# ── Main frame ────────────────────────────────────────────────────────────────
frame = tk.Frame(window, bg=BG)
frame.pack(fill='both', expand=True)

for c in range(3):
    frame.columnconfigure(c, weight=1)

# ── Title ─────────────────────────────────────────────────────────────────────
title_font = font.Font(family='Helvetica', size=22, weight='bold')
tk.Label(
    frame,
    text="Smart Multicontrol System",
    font=title_font, bg=BG, fg='#1a1a2e'
).grid(row=0, column=0, columnspan=3, pady=(20, 4))

sub_font = font.Font(family='Helvetica', size=12)
tk.Label(
    frame,
    text="Control your PC with  Hands  \u00b7  Eyes  \u00b7  Voice",
    font=sub_font, bg=BG, fg='#666'
).grid(row=1, column=0, columnspan=3, pady=(0, 10))

# ── Hero image ────────────────────────────────────────────────────────────────
tk.Label(frame, image=img_man, bg=BG).grid(
    row=2, column=0, columnspan=3, pady=(0, 16))

# ── Button factory ────────────────────────────────────────────────────────────
BTN_FONT = font.Font(family='Helvetica', size=15, weight='bold')

# Track buttons for dynamic updates
_mode_buttons = {}

def _btn(text, color, img, mode):
    btn = tk.Button(
        frame,
        text=f'  {text}',
        font=BTN_FONT,
        fg=color,
        bg='white',
        activebackground='#e8eeff',
        image=img,
        compound='left',
        relief='raised',
        bd=2,
        padx=22,
        pady=14,
        cursor='hand2',
        command=lambda m=mode: _toggle_mode(m)
    )
    _mode_buttons[mode] = (btn, text, color)
    return btn

# ── Row 3: VoiceBot ···· (centre column empty) ···· Keyboard ──────────────────
_btn('VoiceBot', '#27ae60', img_bot,  Mode.VOICE).grid(
    row=3, column=0, padx=40, pady=(0, 14), sticky='e')

_btn('Keyboard', '#c0392b', img_kbd,  Mode.KEYBOARD).grid(
    row=3, column=2, padx=40, pady=(0, 14), sticky='w')

# ── Row 4: Eye Ctrl ···· Exit ···· Gesture ────────────────────────────────────
_btn('Eye Ctrl', '#2980b9', img_eye,  Mode.EYE).grid(
    row=4, column=0, padx=40, pady=(0, 14), sticky='e')

tk.Button(
    frame,
    image=img_exit,
    bg=BG,
    activebackground='#ffcccc',
    relief='flat',
    bd=0,
    cursor='hand2',
    command=window.quit
).grid(row=4, column=1, padx=40, pady=(0, 14))

_btn('Gesture', '#e67e22', img_hand, Mode.GESTURE).grid(
    row=4, column=2, padx=40, pady=(0, 14), sticky='w')

# ── Row 5: Status bar ────────────────────────────────────────────────────────
status_font = font.Font(family='Helvetica', size=11)
status_var = tk.StringVar(value='No active modes  |  F1 Voice · F2 Eye · F3 Gesture · F4 Keyboard')
status_label = tk.Label(
    frame,
    textvariable=status_var,
    font=status_font,
    bg='#dfe6e9',
    fg='#2d3436',
    relief='sunken',
    bd=1,
    padx=10,
    pady=6,
)
status_label.grid(row=5, column=0, columnspan=3, sticky='ew', padx=20, pady=(0, 12))

def _refresh_status(_mode=None, _is_active=None):
    """Update the status bar and button colours to reflect current modes."""
    active = hub.active_modes()
    if active:
        names = '  ·  '.join(m.name.capitalize() for m in active)
        status_var.set(f'Active: {names}  |  F1 Voice · F2 Eye · F3 Gesture · F4 Keyboard')
    else:
        status_var.set('No active modes  |  F1 Voice · F2 Eye · F3 Gesture · F4 Keyboard')

    for m, (btn, text, color) in _mode_buttons.items():
        if hub.is_active(m):
            btn.configure(bg='#d5f5e3', fg='#1e8449', text=f'  ■ {text}')
        else:
            btn.configure(bg='white', fg=color, text=f'  {text}')

# Register hub listeners so status updates when modes change (from any source)
for _m in Mode:
    hub.on_change(_m, lambda is_active, m=_m: window.after(0, _refresh_status, m, is_active))

# ── F-key hotkeys ─────────────────────────────────────────────────────────────
window.bind('<F1>', lambda e: _toggle_mode(Mode.VOICE))
window.bind('<F2>', lambda e: _toggle_mode(Mode.EYE))
window.bind('<F3>', lambda e: _toggle_mode(Mode.GESTURE))
window.bind('<F4>', lambda e: _toggle_mode(Mode.KEYBOARD))
window.bind('<Escape>', lambda e: _stop_all_modes())

# ── Auto-launch Proton voice assistant on startup ─────────────────────────────
hub.start(Mode.VOICE)
log.info("Auto-launching Proton voice assistant on startup")
Thread(target=proton_chat, daemon=True).start()
# Give the GUI a moment then refresh button states
window.after(500, _refresh_status)

window.mainloop()