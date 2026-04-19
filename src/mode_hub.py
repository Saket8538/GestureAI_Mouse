"""
Unified Mode Hub — thread-safe singleton that tracks which input modes are
active (eye, gesture, voice, keyboard).  Every module checks its flag before
running and honours stop requests immediately.

Toggle any mode from:
  - Voice command  ("start eye control", "stop gesture", …)
  - Keyboard shortcut (main.py binds F-keys)
  - GUI button (main.py toggle)

Multiple modes CAN run simultaneously (e.g. eye + voice) — the hub does
NOT enforce mutual exclusion.
"""

import threading
from enum import Enum, auto


class Mode(Enum):
    EYE      = auto()
    GESTURE  = auto()
    VOICE    = auto()
    KEYBOARD = auto()

# Human-readable names for feedback
_MODE_NAMES = {
    Mode.EYE:      "Eye Control",
    Mode.GESTURE:  "Gesture Control",
    Mode.VOICE:    "Voice Assistant",
    Mode.KEYBOARD: "Virtual Keyboard",
}


class _ModeHub:
    """Singleton — import `hub` from this module, never instantiate directly."""

    def __init__(self):
        self._lock = threading.Lock()
        self._active: dict[Mode, bool] = {m: False for m in Mode}
        # Callbacks fired on state change: {Mode: list[callable(bool)]}
        self._listeners: dict[Mode, list] = {m: [] for m in Mode}

    # ── Query ──────────────────────────────────────────────────────────────
    def is_active(self, mode: Mode) -> bool:
        with self._lock:
            return self._active[mode]

    def active_modes(self) -> list[Mode]:
        with self._lock:
            return [m for m, v in self._active.items() if v]

    # ── Mutate ─────────────────────────────────────────────────────────────
    def start(self, mode: Mode):
        with self._lock:
            if self._active[mode]:
                return  # already running
            self._active[mode] = True
        self._notify(mode, True)

    def stop(self, mode: Mode):
        with self._lock:
            if not self._active[mode]:
                return
            self._active[mode] = False
        self._notify(mode, False)

    def toggle(self, mode: Mode) -> bool:
        """Toggle and return the NEW state."""
        with self._lock:
            new_state = not self._active[mode]
            self._active[mode] = new_state
        self._notify(mode, new_state)
        return new_state

    # ── Listeners ──────────────────────────────────────────────────────────
    def on_change(self, mode: Mode, callback):
        """Register callback(is_active: bool) for a mode."""
        with self._lock:
            self._listeners[mode].append(callback)

    def _notify(self, mode: Mode, state: bool):
        with self._lock:
            cbs = list(self._listeners[mode])
        for cb in cbs:
            try:
                cb(state)
            except Exception as e:
                try:
                    from logger import log as _log
                    _log.debug("Mode hub callback error: %s", e)
                except Exception:
                    pass
        # Audio/visual feedback for mode changes
        try:
            from feedback import notify_mode_change
            name = _MODE_NAMES.get(mode, mode.name)
            notify_mode_change(name, state)
        except Exception:
            pass


# Module-level singleton — import this everywhere
hub = _ModeHub()
