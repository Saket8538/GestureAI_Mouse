# Proton — Comprehensive Testing Guide

> **Gesture Controlled Virtual Mouse & Keyboard with AI Voice Assistant**
>
> This guide covers testing **every feature** of the project, step by step.
> Follow the sections in order — earlier sections validate prerequisites that later sections depend on.

---

## Table of Contents

1. [Prerequisites & Environment Setup](#1-prerequisites--environment-setup)
2. [Module Import Verification](#2-module-import-verification)
3. [Configuration System](#3-configuration-system)
4. [AI Brain & .env Setup](#4-ai-brain--env-setup)
5. [Launching the Application](#5-launching-the-application)
6. [GUI & Hotkeys](#6-gui--hotkeys)
7. [Proton Voice Assistant — Basics](#7-proton-voice-assistant--basics)
8. [Voice — Mode Switching](#8-voice--mode-switching)
9. [Voice — Web & Search](#9-voice--web--search)
10. [Voice — Keyboard & Text](#10-voice--keyboard--text)
11. [Voice — Mouse Control](#11-voice--mouse-control)
12. [Voice — Window Management](#12-voice--window-management)
13. [Voice — System Control](#13-voice--system-control)
14. [Voice — File Browser](#14-voice--file-browser)
15. [Voice — Misc & AI Brain Fallback](#15-voice--misc--ai-brain-fallback)
16. [Voice — Confirmation Flow](#16-voice--confirmation-flow)
17. [Voice — Sleep / Wake / Exit](#17-voice--sleep--wake--exit)
18. [Eye Control](#18-eye-control)
19. [Gesture Control](#19-gesture-control)
20. [Virtual Keyboard](#20-virtual-keyboard)
21. [Mode Hub & Multi-Mode](#21-mode-hub--multi-mode)
22. [Chat Interface (Eel)](#22-chat-interface-eel)
23. [Camera Conflict Resolution](#23-camera-conflict-resolution)
24. [Config Hot-Reload](#24-config-hot-reload)
25. [Edge Cases & Stress Tests](#25-edge-cases--stress-tests)
26. [Recent Fixes Verification](#26-recent-fixes-verification)

---

## 1. Prerequisites & Environment Setup

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 1.1 | Python version | `python --version` | 3.10+ (3.12 recommended) |
| 1.2 | Virtual env exists | Check `.venv/` folder in project root | Folder exists with `Lib/site-packages` |
| 1.3 | Auto-venv works | Run `python src/main.py` **without** activating .venv | App starts (auto-venv in `main.py` adds site-packages to `sys.path`) |
| 1.4 | Requirements install | `.venv\Scripts\activate` then `pip install -r requirements.txt` | All 21+ packages install without errors |
| 1.5 | Key packages present | `pip list \| findstr "mediapipe opencv pycaw pyttsx3 eel"` | All listed |
| 1.6 | NumPy present | `python -c "import numpy; print(numpy.__version__)"` | 1.24.0+ |
| 1.7 | Camera available | Open Camera app or `python -c "import cv2; c=cv2.VideoCapture(0); print(c.isOpened()); c.release()"` | `True` |
| 1.8 | Microphone available | Windows Settings → Sound → Input — speak and see level move | Mic detected |
| 1.9 | .env file exists | Check `src/.env` or project root `.env` | File present (see §4 for contents) |
| 1.10 | Icons folder | Verify `icons/` has `mn.png`, `bot.png`, `eye.jpeg`, `hand.png`, `keyboard.png`, `exit.png`, `man.jpeg` | All 7 icon files present |

---

## 2. Module Import Verification

Open a Python shell in the `src/` directory and test each import:

| # | Import | Expected |
|---|--------|----------|
| 2.1 | `import Proton` | No `ModuleNotFoundError` |
| 2.2 | `import eye` | No error |
| 2.3 | `import Gesture_Controller` | No error |
| 2.4 | `import samvk` | No error |
| 2.5 | `import mode_hub` | No error |
| 2.6 | `import ai_brain` | No error |
| 2.7 | `import config_loader` | No error |
| 2.8 | `import action_executor` | No error |
| 2.9 | `import feedback` | No error |
| 2.10 | `from pycaw.pycaw import AudioUtilities` | No error |

---

## 3. Configuration System

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 3.1 | Config loads | `python -c "from config_loader import get; print(get('voice.tts_rate'))"` | `185` |
| 3.2 | Nested key | `get('eye.ema_alpha')` | `0.18` |
| 3.3 | Default value | `get('nonexistent.key', 42)` | `42` |
| 3.4 | Confirmation timeout | `get('voice.confirmation_timeout')` | `30` |
| 3.5 | Edit config.yaml | Change `tts_rate: 185` → `tts_rate: 200`, restart app | TTS speaks noticeably faster |
| 3.6 | Invalid YAML | Add a bad line to config.yaml, start app | App warns and uses defaults gracefully |

---

## 4. AI Brain & .env Setup

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 4.1 | Provider set | `.env` has `PROTON_AI_PROVIDER=gemini` (or openai/claude/ollama) | AI Brain init logs "AI Brain ready — provider=gemini" |
| 4.2 | API key set | `.env` has `PROTON_GEMINI_KEY=...` | No "API key not set" warning |
| 4.3 | Provider=none | Set `PROTON_AI_PROVIDER=none` | "AI Brain disabled" in logs; keyword matching still works |
| 4.4 | Bad API key | Set an invalid key | "AI Brain init failed" warning; app still starts |
| 4.5 | 429 rate limit | (Trigger by rapid commands) | Says "AI service is busy right now. Please try again in a moment." — does **NOT** fall through to Google search |
| 4.6 | Ollama offline | Set provider=ollama with no server running | Falls back gracefully |

---

## 5. Launching the Application

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 5.1 | Normal launch | `cd src && python main.py` | GUI window appears (1080×750), centred on screen |
| 5.2 | Auto-launch Proton | Just launch — don't click anything | Proton voice starts automatically, greets with "Good morning/afternoon/evening" |
| 5.3 | Chat window | After launch | Eel chat window opens on `localhost:27005` |
| 5.4 | VoiceBot button green | After auto-launch | VoiceBot button shows green "■ VoiceBot" |
| 5.5 | Status bar | Check bottom of window | Shows "Active: Voice  |  F1 Voice · F2 Eye · F3 Gesture · F4 Keyboard" |
| 5.6 | Window not resizable | Try to resize | Window stays fixed at 1080×750 |
| 5.7 | Window icon | Check title bar | Custom icon (`mn.png`) displayed |

---

## 6. GUI & Hotkeys

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 6.1 | F1 toggle Voice | Press F1 (Voice already active) | Voice stops, button turns white; press again → restarts |
| 6.2 | F2 start Eye | Press F2 | Eye control starts, camera opens, button green |
| 6.3 | F3 start Gesture | Press F3 | Gesture control starts, button green |
| 6.4 | F4 start Keyboard | Press F4 | Virtual keyboard appears on camera feed |
| 6.5 | Escape stops all | Start multiple modes, press ESC | All modes stop, all buttons white, status shows "No active modes" |
| 6.6 | Button click toggle | Click "Eye Ctrl" button | Eye starts first click, stops second click |
| 6.7 | Multi-mode active | Press F2 + F3 together | Both Eye and Gesture listed in status bar |
| 6.8 | Exit button | Click centre exit icon | Application closes |
| 6.9 | Button visual feedback | Start a mode | Button turns green with "■" prefix; stop → white again |

---

## 7. Proton Voice Assistant — Basics

> **Prerequisite**: Proton auto-launches on app start (§5.2). Speak clearly into microphone.

| # | Test (say →) | Expected Response |
|---|-------------|-------------------|
| 7.1 | "hello" / "hi" / "hey" | Greets you back |
| 7.2 | "good morning" | Appropriate time-based greeting |
| 7.3 | "what is your name" | "I am Proton, your personal assistant" |
| 7.4 | "how are you" | Positive response |
| 7.5 | "thank you" | "You're welcome" or similar |
| 7.6 | "what time is it" | Speaks current time |
| 7.7 | "what is the date" / "today's date" | Speaks current date |
| 7.8 | "help" / "what can you do" | Lists all available features |
| 7.9 | "tell me a joke" | Random programming/general joke |
| 7.10 | (silence for 7s) | No response, no crash (phrase_time_limit = 7s) |

---

## 8. Voice — Mode Switching

| # | Test (say →) | Expected |
|---|-------------|----------|
| 8.1 | "start eye control" | Eye control launches, camera opens |
| 8.2 | "stop eye" / "close eye control" | Eye control stops |
| 8.3 | "start gesture" | Gesture control launches |
| 8.4 | "switch to keyboard" | Keyboard starts (others may continue) |
| 8.5 | "stop all" / "stop everything" | All modes stop except Voice |
| 8.6 | "hands free mode" / "reading mode" | Eye-only preset (stops gesture + keyboard) |
| 8.7 | "typing mode" / "writer mode" | Keyboard-only preset |
| 8.8 | "presentation mode" / "demo mode" | Gesture-only preset |
| 8.9 | "what modes are active" | Lists currently running modes |
| 8.10 | "I control" (misrecognition of "eye") | Correctly interprets as "eye" and toggles |
| 8.11 | "jester" (misrecognition of "gesture") | Correctly interprets as "gesture" |
| 8.12 | "stop it" (after starting gesture) | Stops the last-used mode (gesture) |
| 8.13 | "toggle eye" | Eye toggles on/off |
| 8.14 | "start voice" from chat window | No crash (already in Voice mode) |
| 8.15 | "enable gesture control" | Gesture launches |

---

## 9. Voice — Web & Search

| # | Test (say →) | Expected |
|---|-------------|----------|
| 9.1 | "open youtube" | YouTube opens in browser |
| 9.2 | "play lofi on youtube" | YouTube search for "lofi" opens |
| 9.3 | "open google" | Google.com opens |
| 9.4 | "open github" | GitHub.com opens |
| 9.5 | "open stack overflow" | stackoverflow.com opens |
| 9.6 | "search how to cook pasta" | Google search opens for "how to cook pasta" |
| 9.7 | "google machine learning" | Google search for "machine learning" |
| 9.8 | "navigate to Times Square" | Google Maps opens with "Times Square" |
| 9.9 | "weather" | Google weather opens |
| 9.10 | "weather in London" | Weather for London shown |
| 9.11 | "news" | Google News opens |
| 9.12 | "latest cricket" | Google News search for "cricket" |
| 9.13 | "translate hello to Spanish" | Google Translate opens |
| 9.14 | "wikipedia python programming" | Wikipedia article or search |
| 9.15 | "python compiler" | Online Python compiler opens |
| 9.16 | "search amazon for headphones" | Amazon search for "headphones" |
| 9.17 | "open spotify" | Spotify web opens |
| 9.18 | "open gmail" | Gmail opens |
| 9.19 | "play music" | YouTube music search |
| 9.20 | "location" then "central park" | Two-step: asks for place, then opens Maps |

---

## 10. Voice — Keyboard & Text

| # | Test (say →) | Expected |
|---|-------------|----------|
| 10.1 | "type hello world" | "hello world" typed into active window |
| 10.2 | "press enter" | Enter key pressed |
| 10.3 | "press tab" | Tab key pressed |
| 10.4 | "press escape" | Escape key pressed |
| 10.5 | "press space" | Space key pressed |
| 10.6 | "press delete" | Delete key pressed |
| 10.7 | "select all" | Ctrl+A fires |
| 10.8 | "copy" | Ctrl+C fires |
| 10.9 | "paste" | Ctrl+V fires |
| 10.10 | "undo" | Ctrl+Z fires |
| 10.11 | "redo" | Ctrl+Y fires |
| 10.12 | "save" | Ctrl+S fires |
| 10.13 | "new tab" | Ctrl+T opens new browser tab |
| 10.14 | "close tab" | Ctrl+W closes tab |
| 10.15 | "go back" | Alt+Left (browser back) |
| 10.16 | "go forward" | Alt+Right (browser forward) |
| 10.17 | "zoom in" | Ctrl+Plus fires |
| 10.18 | "zoom out" | Ctrl+Minus fires |
| 10.19 | "refresh" | Ctrl+R (page refresh) |
| 10.20 | "read clipboard" | Speaks clipboard content aloud |

---

## 11. Voice — Mouse Control

| # | Test (say →) | Expected |
|---|-------------|----------|
| 11.1 | "click" / "left click" | Left mouse click at current position |
| 11.2 | "right click" | Right mouse click |
| 11.3 | "double click" | Double left click |
| 11.4 | "scroll up" | Scrolls up ~5 lines |
| 11.5 | "scroll down" | Scrolls down ~5 lines |
| 11.6 | "page up" | Page up |
| 11.7 | "page down" | Page down |
| 11.8 | "select text" / "start selecting" | Mouse down (hold) |
| 11.9 | "stop selecting" | Mouse up (release) |

---

## 12. Voice — Window Management

| # | Test (say →) | Expected |
|---|-------------|----------|
| 12.1 | "minimize" | Active window minimizes |
| 12.2 | "maximize" | Active window maximizes |
| 12.3 | "full screen" | F11 toggles fullscreen |
| 12.4 | "switch window" / "alt tab" | Alt+Tab fires |
| 12.5 | "show desktop" | Win+D |
| 12.6 | "close window" | Asks for confirmation → say "confirm" → Alt+F4 |
| 12.7 | "close window" → "cancel" | Confirmation cancelled, no action |

---

## 13. Voice — System Control

| # | Test (say →) | Expected |
|---|-------------|----------|
| 13.1 | "volume up" | System volume increases ~10% |
| 13.2 | "volume down" | System volume decreases ~10% |
| 13.3 | "mute" | Audio muted |
| 13.4 | "unmute" | Audio unmuted |
| 13.5 | "brightness up" | Screen brightness increases ~10% |
| 13.6 | "brightness down" | Screen brightness decreases ~10% |
| 13.7 | "take a screenshot" / "capture screen" | Screenshot saved/taken |
| 13.8 | "take a photo" / "open camera" | Camera app opens |
| 13.9 | "lock screen" | Asks confirmation → "confirm" → screen locks |
| 13.10 | "lock screen" → "cancel" | Cancelled, no lock |

---

## 14. Voice — File Browser

| # | Test (say →) | Expected |
|---|-------------|----------|
| 14.1 | "list files" | Lists files/folders in C:\ with numbers |
| 14.2 | "open 1" (after listing) | Opens the first item (folder → enters, file → opens) |
| 14.3 | "back" (inside a folder) | Returns to parent directory |
| 14.4 | "open 999" (invalid index) | Handles gracefully — no crash |
| 14.5 | "list files" → "back" repeatedly | Can navigate up to drive root without error |

---

## 15. Voice — Misc & AI Brain Fallback

| # | Test (say →) | Expected |
|---|-------------|----------|
| 15.1 | "what's the capital of France" | AI Brain responds: "Paris" (or similar) |
| 15.2 | "copy this and paste into notepad" | AI Brain chains: Ctrl+C → open Notepad → Ctrl+V |
| 15.3 | "set a timer for 5 minutes" | AI Brain attempts action or explains limitation |
| 15.4 | (random nonsense phrase) | AI Brain tries to handle; may fall to Google search |
| 15.5 | AI unavailable + unknown command | Falls to Google search as last resort |
| 15.6 | AI 429 rate limit error | Says "AI service is busy right now" — does NOT Google search |
| 15.7 | "just a little" (casual phrase while AI 429) | Says "AI service is busy" — doesn't search "just a little" |

---

## 16. Voice — Confirmation Flow

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 16.1 | Quick confirm | Say "exit" → within 5s say "confirm" | Proton exits |
| 16.2 | Slow confirm (within 30s) | Say "close window" → wait 20s → say "confirm" | Window closes (30s timeout) |
| 16.3 | Cancel | Say "lock screen" → say "cancel" | "Cancelled." — no lock |
| 16.4 | Timeout | Say "lock screen" → wait >30s → say "confirm" | Confirmation expired, "confirm" treated as new command |
| 16.5 | Yes synonyms | Say "exit" → say "yes" | Works same as "confirm" |
| 16.6 | Ok synonym | Say "exit" → say "okay" | Works |
| 16.7 | No synonym | Say "exit" → say "no" | Cancels |
| 16.8 | "Do it" synonym | Say "close window" → "do it" | Closes window |
| 16.9 | "Never mind" synonym | Say "lock screen" → "never mind" | Cancelled |
| 16.10 | Double confirmation | Say "exit" → "confirm" → immediately another command | First exits; second command doesn't run (app closing) |

---

## 17. Voice — Sleep / Wake / Exit

| # | Test (say →) | Expected |
|---|-------------|----------|
| 17.1 | "sleep" / "go to sleep" | "Goodbye! Say 'Proton wake up' when you need me!" — stops listening to commands |
| 17.2 | "hello" (while sleeping) | No response — Proton is asleep |
| 17.3 | "Proton wake up" (while sleeping) | Proton wakes up, greets you |
| 17.4 | "goodbye" / "bye" | Enters sleep mode |
| 17.5 | "exit" → "confirm" | All modes stop, app exits |
| 17.6 | "terminate" → "confirm" | Same as exit |
| 17.7 | "quit proton" → "confirm" | Same as exit |
| 17.8 | "shut down proton" → "confirm" | Same as exit |
| 17.9 | "close proton" → "confirm" | Same as exit |
| 17.10 | "exit" → (wait 35s) → "confirm" | Confirmation expired — "confirm" is treated as a new input |

---

## 18. Eye Control

> **Prerequisite**: Start Eye Control (F2 or say "start eye control"). Camera feed appears.

| # | Test | How | Expected |
|---|------|-----|----------|
| 18.1 | Cursor follows gaze | Look around the screen | Cursor moves smoothly with gaze direction |
| 18.2 | EAR HUD visible | Look at camera feed | Real-time EAR value displayed on overlay |
| 18.3 | Calibration | First 120 frames | "Calibrating…" then "Calibration complete" |
| 18.4 | Left click (quick blink) | Close eyes < 0.4s | Left click at cursor position |
| 18.5 | Right click (slow blink) | Close eyes 0.4–1.5s | Right click at cursor position |
| 18.6 | Double click | Two quick blinks within 0.6s | Double-click fires |
| 18.7 | Drag mode | Close eyes > 1.5s | Mouse-down starts, move gaze, open eyes → mouse-up |
| 18.8 | Dwell-click | Stare at one spot ≥ 1.5s | Auto-click with progress ring |
| 18.9 | Scroll (gaze at edges) | Look at top/bottom 10% of screen | Scrolls up/down respectively |
| 18.10 | Smooth cursor | Move gaze slowly | No jitter (EMA smoothing, deadzone = 3-5px) |
| 18.11 | Cursor speed | Check config `cursor_speed: 1.4` | Cursor covers screen in reasonable gaze range |
| 18.12 | Click cooldown | Blink rapidly | Only one click per 0.8s (cooldown enforced) |
| 18.13 | Q to quit | Press Q on keyboard while camera feed active | Eye control stops, camera releases |
| 18.14 | Average EAR | Blink with both eyes; blink with one eye | Both-eyes blink triggers; one-eye wink less likely to trigger |
| 18.15 | Head tilt scroll | Tilt head up/down | Scrolls accordingly |

---

## 19. Gesture Control

> **Prerequisite**: Start Gesture Control (F3 or say "start gesture"). Camera feed appears.

| # | Test | How | Expected |
|---|------|-----|----------|
| 19.1 | Cursor movement | Show V-gesture (index + middle spread), move hand | Cursor follows hand position |
| 19.2 | Left click | Raise middle finger (MID gesture) | Left click |
| 19.3 | Right click | Raise index finger (INDEX gesture) | Right click |
| 19.4 | Double click | Two fingers closed (TWO_FINGER_CLOSED) | Double click |
| 19.5 | Drag | Make fist (FIST gesture) | Mouse down → drag → release fist → mouse up |
| 19.6 | Scroll (left hand pinch) | Left hand: pinch vertically | Scrolls up/down |
| 19.7 | Horizontal scroll | Left hand: pinch horizontally | Scrolls left/right |
| 19.8 | Volume control | Right hand: pinch and move horizontally | System volume changes |
| 19.9 | Brightness control | Right hand: pinch and move vertically | Screen brightness changes |
| 19.10 | Volume sensitivity | Small pinch movement | Volume changes in reasonable increments (divisor=15) |
| 19.11 | Brightness sensitivity | Small pinch movement | Brightness changes in reasonable increments |
| 19.12 | Pinch threshold | Barely pinch (fingers almost touching) | Only triggers when < 0.15 distance |
| 19.13 | Frame hold | Quick accidental pinch | Requires 3 consecutive frames to trigger |
| 19.14 | Smooth cursor | Move V-gesture slowly | Cursor is smooth (speed damping = 0.7) |
| 19.15 | Both hands | Show both hands | Right = mouse/volume/brightness, Left = scroll |

---

## 20. Virtual Keyboard

> **Prerequisite**: Start Keyboard (F4 or say "start keyboard"). Camera feed with keyboard overlay appears.

| # | Test | How | Expected |
|---|------|-----|----------|
| 20.1 | Key layout visible | Look at camera feed | Full QWERTY layout + SPACE, BKSP, ENTER, TAB, CAPS |
| 20.2 | Hover highlight | Move index fingertip over a key | Key highlights yellow |
| 20.3 | Type letter | Hover over "A" + pinch (index + middle close) | "a" typed into active window |
| 20.4 | CAPS toggle | Pinch CAPS key | CAPS key turns green; subsequent letters are uppercase |
| 20.5 | Space key | Pinch SPACE | Space character typed |
| 20.6 | Backspace | Pinch BKSP | Last character deleted |
| 20.7 | Enter key | Pinch ENTER | Enter key pressed |
| 20.8 | Tab key | Pinch TAB | Tab key pressed |
| 20.9 | Debounce | Pinch and hold on a key | Only one key press (0.4s cooldown) |
| 20.10 | Release required | Pinch, keep pinching, hover to next key | Must release pinch before next key triggers |
| 20.11 | Key release | After each keypress | Key is properly released (no stuck keys) |
| 20.12 | Numbers row | Hover + pinch on "5" | "5" typed |
| 20.13 | Special characters | Hover + pinch on ";" or "/" | Character typed |
| 20.14 | Rapid typing | Type "hello" quickly | All 5 letters registered with proper debounce |

---

## 21. Mode Hub & Multi-Mode

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 21.1 | Single mode | Start only Eye | `hub.active_modes()` returns `[Mode.EYE]` |
| 21.2 | Multiple modes | Start Eye + Gesture | Both listed in status bar |
| 21.3 | Ask active modes | Say "what modes are active" | Proton lists all running modes |
| 21.4 | Stop specific mode | Say "stop gesture" | Only gesture stops; eye continues |
| 21.5 | Stop all | Say "stop all" or press ESC | All modes stop (Voice may continue) |
| 21.6 | Thread safety | Rapidly toggle modes (F2 F3 F4 F2 F3) | No crash, no duplicate threads |
| 21.7 | Mode change sound | Start any mode | System feedback sound plays (if enabled) |
| 21.8 | Status bar updates | Toggle modes via different methods | Status bar always reflects true state |

---

## 22. Chat Interface (Eel)

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 22.1 | Chat opens | Launch app | Browser/eel window opens at `localhost:27005` |
| 22.2 | Type command in chat | Type "hello" in chat input, press Enter | Proton responds in both chat and voice |
| 22.3 | Voice response in chat | Say "what time is it" via mic | Response appears in chat window too |
| 22.4 | Port reuse | Close and reopen app | No "port 27005 in use" error (SO_REUSEADDR) |
| 22.5 | Chat bypasses wake word | Set `require_wake_word: true` in config; type "hello" in chat | Responds (chat text is exempt from wake-word check) |
| 22.6 | Long text in chat | Type a long sentence | Handled without truncation |

---

## 23. Camera Conflict Resolution

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 23.1 | Eye → Gesture (same camera) | Start Eye, then say "start gesture" | Eye auto-stops, waits 1.5s, Gesture starts. "Auto-stopped eye (camera in use)" |
| 23.2 | Gesture → Keyboard | Start Gesture, then start Keyboard | Gesture auto-stops, Keyboard starts |
| 23.3 | No conflict (different cameras) | Set `eye.camera_index: 0` and `gesture.camera_index: 1` (if dual cameras) | Both can run simultaneously |
| 23.4 | Camera release wait | Auto-stop triggers | 1.5s delay before new mode starts (camera release) |
| 23.5 | Voice + Eye coexist | Start Voice + Eye | Both run (Voice doesn't use camera) |

---

## 24. Config Hot-Reload

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 24.1 | Change TTS rate | Edit `tts_rate: 185` → `tts_rate: 220`, restart voice | Speech is faster |
| 24.2 | Change cursor speed | Edit `eye.cursor_speed: 1.4` → `2.0`, restart Eye | Cursor moves faster |
| 24.3 | Change pinch threshold | Edit `gesture.pinch_threshold: 0.15` → `0.25` | Need bigger pinch to trigger |
| 24.4 | Change confirmation timeout | Edit `voice.confirmation_timeout: 30` → `10` | Confirmation expires in 10s |
| 24.5 | Change scroll cooldown | Edit `eye.scroll_cooldown: 0.25` → `0.5` | Slower scroll rate |

---

## 25. Edge Cases & Stress Tests

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 25.1 | No microphone | Unplug mic, start app | App starts; voice recording fails gracefully ("check Internet" or silent) |
| 25.2 | No camera | Cover/unplug camera, start Eye/Gesture/Keyboard | "Failed to launch" message; no crash |
| 25.3 | Rapid mode toggling | Press F2 F2 F2 F2 quickly | Eye starts/stops without duplicated threads or crash |
| 25.4 | Speak while TTS talking | Interrupt Proton mid-sentence | Next mic input works normally |
| 25.5 | Very long voice input | Speak for >7s continuously | Phrase cut at `phrase_time_limit` (7s); processes what it captured |
| 25.6 | Empty voice (silence) | Don't speak, wait for timeout | No crash, no processing of empty string |
| 25.7 | Macro chaining | "open notepad and then type hello" | Opens Notepad, then types "hello" (up to 4 steps) |
| 25.8 | Unrecognized speech | Mumble gibberish | `UnknownValueError` caught; debug-level log only |
| 25.9 | Network down | Disconnect WiFi, say a command | "Sorry my Service is down. Plz check your Internet connection" |
| 25.10 | config.yaml missing | Rename config.yaml, start app | App uses hardcoded defaults; warn in log |
| 25.11 | Multiple app instances | Launch `python main.py` twice | Second instance gracefully handles port conflict |
| 25.12 | ESC after exit confirmation | Say "exit" → press ESC | All modes stop; confirmation may remain until timeout |

---

## 26. Recent Fixes Verification

These tests specifically validate bugs that were fixed in recent sessions.

| # | Fix | Test | Expected |
|---|-----|------|----------|
| 26.1 | Eye blink precision | Blink both eyes → click; wink one eye → no click | Uses average EAR — both-eye blink triggers, single-eye wink does not |
| 26.2 | Confirmation timeout 30s | Say "exit" → wait 25s → say "confirm" | Still confirms (30s window) |
| 26.3 | AI 429 no Google search | Trigger rate limit → say something | "AI service is busy right now" — NOT a Google search |
| 26.4 | Auto-launch Proton | Start app fresh | Proton launches automatically — no button click needed |
| 26.5 | Gesture volume sensitivity | Right-hand pinch horizontal | Volume changes in small, usable increments (divisor=15) |
| 26.6 | Keyboard key release | Type letters on virtual keyboard | Keys release properly (no stuck keys) |
| 26.7 | Camera retry | Start Eye → camera busy briefly | Retries camera open; succeeds once available |
| 26.8 | Empty frame logging | Eye/Gesture running | Empty camera frames logged at DEBUG level (not flooding INFO) |
| 26.9 | Voice mode in switch map | Say "start voice" from chat | No crash; voice is recognized in mode-switch map |
| 26.10 | Port 27005 reuse | Close app, relaunch quickly | Chat port binds successfully (SO_REUSEADDR) |
| 26.11 | ESC stops all modes | Start all 4 modes, press ESC | All modes stop, buttons reset to white |
| 26.12 | Auto-venv detection | Run `python src/main.py` without venv active | App finds `.venv/Lib/site-packages` automatically |
| 26.13 | Mode words don't leak to search | Say "start gesture control mode" | Launches gesture — does NOT Google-search "start gesture control mode" |
| 26.14 | EAR HUD display | Start Eye Control, look at camera feed | Real-time EAR value shown on overlay |
| 26.15 | Camera conflict auto-stop | Start Eye then Gesture (same camera) | Eye auto-stops with notification, 1.5s wait, then Gesture starts |

---

## Quick Smoke Test (5 minutes)

Run these 10 tests first to verify the app is fundamentally working:

1. **Launch**: `cd src && python main.py` → GUI appears, Proton auto-starts
2. **Voice greeting**: Proton says "Good morning/afternoon/evening"
3. **Voice command**: Say "what time is it" → speaks time
4. **Mode switch**: Say "start eye control" → eye launches
5. **Eye click**: Quick blink → click happens
6. **Stop mode**: Say "stop eye" → eye stops
7. **Gesture**: Press F3 → V-gesture moves cursor
8. **Keyboard**: Press F4 → hover + pinch types letter
9. **ESC**: Press Escape → all modes stop
10. **Exit**: Say "exit" → "confirm" → app closes

---

*Last updated: Session 7 — confirmation timeout fix, AI 429 handling, Proton auto-launch*
