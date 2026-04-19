# Gesture Controlled Virtual Mouse and Keyboard

> Control your entire PC using only your **hands**, **eyes**, and **voice** — no mouse, no keyboard required.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Hardware & Software Requirements](#3-hardware--software-requirements)
4. [Installation & Setup](#4-installation--setup)
5. [Launching the Application](#5-launching-the-application)
6. [Feature 1 — Hand Gesture Mouse](#6-feature-1--hand-gesture-mouse)
7. [Feature 2 — Eye Gaze Mouse](#7-feature-2--eye-gaze-mouse)
8. [Feature 3 — Virtual Air Keyboard](#8-feature-3--virtual-air-keyboard)
9. [Feature 4 — Voice Bot (Proton)](#9-feature-4--voice-bot-proton)
10. [Tips for Best Performance](#10-tips-for-best-performance)
11. [Project File Structure](#11-project-file-structure)
12. [Troubleshooting](#12-troubleshooting)
13. [Contributors](#13-contributors)

---

## 1. Project Overview

The **Gesture Controlled Virtual Mouse and Keyboard** is an accessibility and productivity system that replaces traditional input devices entirely. Using only a standard webcam and microphone, users can:

- Move the mouse cursor and perform all click operations using **hand gestures in mid-air**
- Move the cursor and click using only **eye movements and blinks**
- Type on a full keyboard by **pointing fingers** at virtual on-screen keys
- Issue **voice commands** to search the web, navigate files, control the system, and more

The system is built with **MediaPipe**, **OpenCV**, **CVzone**, **PyAutoGUI**, **pyttsx3**, and **SpeechRecognition**. It runs entirely on a standard PC — no special hardware, gloves, or external sensors needed.

**Ideal for:** People with mobility impairments, touchless control environments, accessibility research, and HCI demonstrations.

---

## 2. System Architecture

```
main.py  (Tkinter Launcher GUI)
│
├── Gesture_Controller.py   — MediaPipe hand landmark → mouse/scroll/volume/brightness
├── eye.py                  — MediaPipe FaceMesh iris → cursor + blink → click/drag/scroll
├── samvk.py                — CVzone hand detector → virtual keyboard typing
└── Proton.py               — Speech recognition + pyttsx3 TTS + eel web chat UI
    └── app.py              — eel server (Chrome mini-window chat interface)
        └── web/
            └── index.html  — Chat UI rendered in Chrome
```

Each module runs in its own **daemon thread** so the launcher stays responsive while any mode is active.

---

## 3. Hardware & Software Requirements

### Hardware
| Component | Requirement |
|---|---|
| Webcam | Any USB or built-in webcam (720p or higher recommended) |
| Microphone | Built-in or external (for VoiceBot only) |
| OS | Windows 10 / 11 |
| RAM | 4 GB minimum, 8 GB recommended |
| CPU | Intel i5 / Ryzen 5 or better (MediaPipe is CPU-intensive) |

### Software
| Package | Purpose |
|---|---|
| Python 3.10–3.12 | Runtime |
| mediapipe | Hand & face landmark detection |
| opencv-python | Webcam capture + drawing |
| cvzone | High-level hand tracking helpers |
| pyautogui | Mouse & keyboard control |
| pynput | Low-level keyboard events |
| pycaw | Windows audio volume control |
| screen-brightness-control | Windows display brightness |
| pyttsx3 | Text-to-speech (offline) |
| SpeechRecognition | Voice input (Google API) |
| wikipedia | Wikipedia summaries |
| eel | Python ↔ JavaScript bridge for chat UI |
| Pillow | Image loading in the launcher |

---

## 4. Installation & Setup

### Step 1 — Clone the repository
```bash
git clone https://github.com/shriakshita/Gesture-Controlled-Virtual-Mouse-and-Keyboard.git
cd Gesture-Controlled-Virtual-Mouse-and-Keyboard
```

### Step 2 — Create a virtual environment
```bash
python -m venv .venv
```

### Step 3 — Activate the virtual environment
```bash
# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# Windows (CMD)
.\.venv\Scripts\activate.bat
```

### Step 4 — Install all dependencies
```bash
pip install -r requirements.txt
```

> **Note:** If `pyaudio` fails to install via pip, download the matching `.whl` from  
> https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio and install with:
> ```bash
> pip install PyAudio‑0.2.11‑cpXX‑cpXX‑win_amd64.whl
> ```

### Step 5 — Verify the install
```bash
cd src
python -c "import cv2, mediapipe, pyautogui, cvzone, pycaw, screen_brightness_control, pyttsx3, speech_recognition, wikipedia, eel; print('All OK')"
```

### Step 6 — Run project smoke test
```bash
cd ..
python tests/smoke_test.py
```

---

## 5. Launching the Application

```bash
cd src
python main.py
```

The launcher window appears with **5 buttons**:

| Button | Colour | Opens |
|---|---|---|
| **VoiceBot** | Green | Proton AI voice assistant + chat window |
| **Keyboard** | Red | Virtual air keyboard (webcam window) |
| **Eye Ctrl** | Blue | Eye gaze mouse (webcam window) |
| **Gesture** | Orange | Hand gesture mouse (webcam window) |
| **Exit** (icon) | Centre | Closes the launcher |

> Each button launches its module in a **background thread** — you can run multiple modes simultaneously (e.g., Gesture mouse + VoiceBot at the same time).

---

## 6. Feature 1 — Hand Gesture Mouse

**File:** `src/Gesture_Controller.py`  
**Button:** `Gesture` (orange)

### How it works
MediaPipe detects 21 hand landmarks in real time. Finger states are encoded as a bitmask and matched to gesture classes. The **right hand (major)** drives the mouse; the **left hand (minor)** controls scroll.

### Gesture Reference Table

| Gesture | Hand | How to Form It | Action |
|---|---|---|---|
| **V-Gesture** | Right | Index + middle fingers up, spread apart (like a ✌ peace sign) | **Move cursor** |
| **Left Click** | Right | Start from V-Gesture → fold middle finger down | **Left click** |
| **Right Click** | Right | Start from V-Gesture → fold index finger down | **Right click** |
| **Double Click** | Right | Start from V-Gesture → close both fingers together (touch) | **Double click** |
| **Drag / Drop** | Right | Make a ✊ fist, move hand | **Hold mouseDown + move**; open fist to release |
| **Volume Up/Down** | Right | Pinch (thumb+index) → move hand **up** or **down** | **System volume ±** |
| **Brightness Up/Down** | Right | Pinch (thumb+index) → move hand **left** or **right** | **Screen brightness ±** |
| **Scroll Up/Down** | Left | Pinch (thumb+index) → move hand **up** or **down** | **Scroll vertically** |
| **Scroll Left/Right** | Left | Pinch (thumb+index) → move hand **left** or **right** | **Scroll horizontally** |
| **Neutral (Palm)** | Either | Open palm facing camera | **No action** — resting position |

### Visual Feedback
The webcam window shows the live hand skeleton with all 21 landmarks connected. The cursor moves in real time as your hand moves.

### Quitting
Press **Enter** on the OpenCV webcam window.

### Performance Tips
- Keep your hand **40–60 cm** from the camera
- Ensure **good lighting** (avoid backlight)
- Hold each gesture still for ~5 frames before the action fires (built-in noise filter)
- If you have two hands in frame, the system auto-assigns major/minor by handedness
- **Cursor speed** is set to 0.7× by default — gentler for users with hand tremor. To adjust, change `Controller.CURSOR_SPEED` in `Gesture_Controller.py` (range: 0.3 slow → 1.5 fast)

---

## 7. Feature 2 — Eye Gaze Mouse

**File:** `src/eye.py`  
**Button:** `Eye Ctrl` (blue)

### How it works
MediaPipe FaceMesh tracks **468 face landmarks** including the iris (landmarks 474–477). The **centroid of all 4 iris landmarks** is averaged to reduce noise. An **Exponential Moving Average (EMA)** filter smooths cursor movement every frame. Blink detection uses a per-person auto-calibrated threshold measured from your open-eye gap in the first 40 frames. The full screen is reached via **gaze range normalisation** that auto-detects your personal eye movement limits over the first 4 seconds.

### Accessibility Enhancements

| Enhancement | What it does |
|---|---|
| **Iris centroid (4-pt avg)** | Averages landmarks 474–477 → 4× less noisy than a single point |
| **Median + Double EMA smoothing (α=0.08)** | Median pre-filter removes spikes, then two EMA passes stabilize gaze while keeping movement responsive |
| **Auto-blink calibration** | Samples your open-eye gap for 40 frames → sets your personal blink threshold (no manual tuning needed) |
| **Gaze range normalisation** | Measures your eye movement range for 4 s at startup → cursor reaches every screen corner |
| **Deadzone + speed scaling** | Ignores micro-jitter and supports configurable cursor speed (`eye.cursor_speed`) |
| **Dwell-to-click** | Hold gaze still for 1.5 s → auto left-click with animated countdown arc (for users who cannot blink) |

### Controls Reference

| Action | How to Perform |
|---|---|
| **Move cursor** | Simply **look** at any point on the screen — the EMA-smoothed iris centroid follows your gaze |
| **Left Click** | Quick **both-eye blink** (< 0.4 s) |
| **Right Click** | Slow **both-eye blink** (0.4–1.5 s) |
| **Double Click** | Two quick blinks within 0.6 s |
| **Start Text Selection / Drag** | Hold both eyes closed for more than 1.5 seconds → `mouseDown` activates |
| **End Text Selection / Drop** | Open eyes after dragging → `mouseUp` fires |
| **Dwell Click (auto)** | Simply **hold your gaze still** for 1.5 seconds — an orange arc countdown appears, then left-click fires automatically. No blinking needed. |
| **Scroll Up** | Look at the **top 10%** of the screen or tilt head up |
| **Scroll Down** | Look at the **bottom 10%** of the screen or tilt head down |

### On-Screen HUD
A black bar at the very top of the webcam window shows all controls as a reminder:
```
Blink=Click | SlowBlink=RClick | LongHold=Drag | Tilt=Scroll | Q=Quit
```
A green progress bar at the bottom of the frame shows gaze calibration progress on startup (first 4 seconds).  
The current action (e.g. `LEFT CLICK`, `DWELL 65%`, `SELECTING...`) is displayed in green text in the centre of the frame.

### Quitting
Press **Q** on the OpenCV webcam window.

### Performance Tips
- Sit **50–70 cm** from the camera
- Face the camera **straight on** — avoid extreme head angles
- Ensure your **face is evenly lit** (avoid strong sidelighting)
- During the **4-second gaze calibration** at startup, slowly look at all four screen corners — this sets your personal range
- The `CLICK_COOLDOWN` is 1 second — rapid accidental blinks are ignored
- Use `SELECTING...` mode to highlight text: hold left eye, move gaze across text, open eye to release
- **Dwell click** is ideal for users with blink impairment — just stare at a target for 1.5 s

---

## 8. Feature 3 — Virtual Air Keyboard

**File:** `src/samvk.py`  
**Button:** `Keyboard` (red)

### How it works
CVzone's `HandDetector` tracks your hand. Your **index fingertip (landmark 8)** acts as the pointer. Hovering over a key highlights it yellow. **Pinching** index + middle finger together (distance < 30 px) confirms the keypress (turns green), which sends the actual keystroke to the active OS window via `pynput`.

### Keyboard Layout

```
[ 1 ][ 2 ][ 3 ][ 4 ][ 5 ][ 6 ][ 7 ][ 8 ][ 9 ][ 0 ]
[ Q ][ W ][ E ][ R ][ T ][ Y ][ U ][ I ][ O ][ P ]
[ A ][ S ][ D ][ F ][ G ][ H ][ J ][ K ][ L ][ ; ]
[ Z ][ X ][ C ][ V ][ B ][ N ][ M ][ , ][ . ][ / ]
[         SPACE          ][    BKSP    ]
```

### Key Actions

| Key | Result |
|---|---|
| Any letter / number / symbol | Types that character into the active window |
| `SPACE` | Inserts a space |
| `BKSP` | Deletes the last character (Backspace) |

### Visual Feedback
- **Orange** = default key state
- **Yellow** = your fingertip is hovering over this key
- **Green** = key is being pressed (pinch detected)
- **White bar at bottom** = shows the last 22 characters you have typed

### Quitting
Press **Q** on the OpenCV webcam window.

### Performance Tips
- Stand or sit with the webcam in front of you, **hand clearly visible**
- Point your hand toward the camera so fingertips are clearly separated
- After each keypress there is a **0.2 s cooldown** to prevent double-typing
- To type into a specific app (Notepad, browser, etc.), click that app first to give it focus, then activate the keyboard

---

## 9. Feature 4 — Voice Bot (Proton)

**File:** `src/Proton.py`  
**Button:** `VoiceBot` (green)

### How it works
A Chrome mini-window (350×480 px) opens in the corner of your screen powered by `eel`. You can either **speak** to Proton via your microphone, or **type** in the chat box. Proton responds by both **speaking aloud** (pyttsx3 TTS) and displaying text in the chat window.

> By default, Proton accepts natural voice commands without requiring the wake word.  
> Set `voice.require_wake_word: true` in `config.yaml` if you want strict wake-word gating.  
> Unknown commands are handled autonomously via AI Brain fallback first, then Google search.
> Multi-step chains are supported (example: `open notepad and then type hello`).
> Risky actions (lock screen, close window, exit proton) require `confirm` / `cancel`.

### How intent dispatch works
The old fixed keyword list has been replaced by a **priority-ranked intent dispatcher**:
1. File-browser mode (intercepts "open 3", "back" when browsing files)
2. Greetings / identity / date / time
3. Play / YouTube (handles any "play X" phrase)
4. Maps & navigation ("navigate to", "directions to", "where is", "open google maps")
5. Weather, news, translate
6. Wikipedia
7. Online compiler (Python / Java / C++ / Replit / Colab)
8. Google search
9. Screenshot, typing, mouse, keyboard shortcuts, volume
10. **Generic OPEN** — opens **any** app, website, or service by name via an 80-entry lookup table
11. List files, jokes, sleep, exit
12. **Smart fallback** — unknown command → AI Brain interpretation, then Google search if still unresolved

### Autonomous Voice Features
- **Mode presets**: `hands free mode`, `typing mode`, `presentation mode`
- **Command chaining**: `open notepad and then type hello world`
- **Context carry-over**: `start eye` then `stop it`
- **Safety confirmation**: Proton asks before lock/close/exit

### Complete Voice Command Reference

#### Greetings & Information
| Say | Response |
|---|---|
| `proton hello` / `proton hi` / `proton hey` | Greeting based on time of day |
| `proton what is your name` / `proton who are you` | "My name is Proton!" |
| `proton how are you` | Friendly status reply |
| `proton time` | Current system time |
| `proton date` / `proton today's date` | Today's full date |
| `proton wikipedia black holes` | 2-sentence Wikipedia summary (opens page if ambiguous) |
| `proton tell me a joke` | Random programmer joke |
| `proton thank you` | "You're welcome!" |

#### Play / YouTube
| Say | Response |
|---|---|
| `proton play shape of you on youtube` | Searches YouTube for "shape of you" |
| `proton play relaxing music` | Searches YouTube for "relaxing music" |
| `proton play music` | Opens YouTube Music |
| `proton open music` | Opens YouTube Music |

#### Open — Any App, Website or Service
Proton checks an **80-entry lookup table** then guesses the URL if unknown.

| Say | Opens |
|---|---|
| `proton open google` | google.com |
| `proton open google maps` | maps.google.com ✅ (was broken before) |
| `proton open youtube` | youtube.com |
| `proton open gmail` | mail.google.com |
| `proton open whatsapp` | web.whatsapp.com |
| `proton open github` | github.com |
| `proton open chatgpt` | chat.openai.com |
| `proton open netflix` | netflix.com |
| `proton open spotify` | open.spotify.com |
| `proton open online compiler` | Programiz Python compiler |
| `proton open colab` | Google Colab |
| `proton open replit` | replit.com |
| `proton open notepad` | Windows Notepad |
| `proton open calculator` | Windows Calculator |
| `proton open file explorer` | Windows File Explorer |
| `proton open task manager` | Windows Task Manager |
| `proton open paint` | MS Paint |
| `proton open anywebsite` | Tries `https://anywebsite.com` |
| `proton launch gesture recognition` | Starts hand gesture mouse |
| `proton stop gesture recognition` | Stops hand gesture mouse |

#### Go to URL by speaking
| Say | Opens |
|---|---|
| `proton go to github dot com` | https://github.com |
| `proton go to stackoverflow dot com` | https://stackoverflow.com |

#### Navigation & Maps
| Say | Response |
|---|---|
| `proton navigate to Eiffel Tower` | Opens Google Maps directions |
| `proton directions to Mumbai Airport` | Opens Google Maps directions |
| `proton where is the Taj Mahal` | Shows location on Google Maps |
| `proton open google maps` | Opens Google Maps |

#### Web & Search
| Say | Response |
|---|---|
| `proton search python tutorials` | Google search |
| `proton google machine learning` | Google search |
| `proton weather in Delhi` | Google weather result |
| `proton news today` | Google News |
| `proton latest news India` | Google News search |
| `proton translate hello to Spanish` | Opens Google Translate |

#### Voice Mouse & Typing
| Say | Response |
|---|---|
| `proton type def hello world` | **Types that text** into the active window |
| `proton click` | Left click at cursor |
| `proton right click` | Right click at cursor |
| `proton double click` | Double click at cursor |
| `proton scroll up` / `proton page up` | Scroll up |
| `proton scroll down` / `proton page down` | Scroll down |

#### Key Presses
| Say | Response |
|---|---|
| `proton press enter` | Enter key |
| `proton press tab` / `proton next field` | Tab key |
| `proton press escape` | Escape key |
| `proton press space` | Spacebar |
| `proton press delete` | Delete key |

#### Keyboard Shortcuts
| Say | Response |
|---|---|
| `proton select all` | Ctrl+A |
| `proton copy` | Ctrl+C |
| `proton paste` | Ctrl+V |
| `proton undo` | Ctrl+Z |
| `proton redo` | Ctrl+Y |
| `proton save file` | Ctrl+S |
| `proton new tab` | Ctrl+T |
| `proton close tab` | Ctrl+W |
| `proton go back` | Alt+Left (browser back) |
| `proton go forward` | Alt+Right (browser forward) |
| `proton zoom in` | Ctrl++ |
| `proton zoom out` | Ctrl+- |
| `proton refresh` | Ctrl+R (page refresh) |
| `proton minimize` | Win+Down |
| `proton maximize` | Win+Up |
| `proton close window` | Alt+F4 |
| `proton screenshot` | Win+PrtSc (saves to Pictures) |

#### Volume
| Say | Response |
|---|---|
| `proton volume up` / `proton louder` | System volume +10% |
| `proton volume down` / `proton quieter` | System volume −10% |
| `proton mute` / `proton silence` | Mute audio |
| `proton unmute` | Unmute audio |

#### File Navigation
| Say | Response |
|---|---|
| `proton list files` | Lists C:\ directory |
| `proton open 3` | Opens item 3 from the list |
| `proton back` | Goes to parent folder |

#### Bot Lifecycle
| Say | Response |
|---|---|
| `proton bye` / `proton sleep` | Bot sleeps — stops responding |
| `proton wake up` | Wakes bot back up |
| `proton exit` / `proton terminate` | Closes VoiceBot window |

#### Smart Fallback
> If Proton does not match a built-in command, it first sends the request to the **AI Brain** for autonomous interpretation.
> If AI Brain cannot resolve it, Proton then performs a **Google search** as the final fallback.
> Example: `proton latest score India vs Australia` → AI fallback or direct Google search with the same query.

### Notes on Voice Recognition
- The bot uses **Google Cloud Speech API** — an internet connection is required
- **Dynamic energy threshold** automatically adapts to room noise
- `pause_threshold = 2.0 s` — waits for slow/speech-impaired speakers to finish
- `phrase_time_limit = 15 s` — you have up to 15 seconds per command
- TTS voice is set to **150 wpm** (slower than default 200) at full volume for clarity

---

## 10. Tips for Best Performance

### General
- Run from the `src/` folder: `cd src && python main.py`
- Close other webcam applications before launching (only one app can own the camera)
- Run on a machine with a **dedicated GPU** for better MediaPipe frame rates

### Lighting
- **Even, front-facing light** gives the best landmark detection
- Avoid sitting with a bright window behind you (backlight confuses the model)

### Camera Placement
| Mode | Optimal Distance | Positioning |
|---|---|---|
| Gesture Mouse | 40–60 cm | Camera at mid-chest height, hand in frame centre |
| Eye Mouse | 50–70 cm | Camera at eye level, face centred and level |
| Virtual Keyboard | 40–70 cm | Camera slightly above, tilted down so both hand and keys are visible |

### Running Multiple Modes Together
You can combine modes — for example:
- **Gesture Mouse + VoiceBot**: Use your hand to move/click and voice to search
- **Eye Mouse + VoiceBot**: Completely hands-free operation

---

## 11. Project File Structure

```
Gesture-Controlled-Virtual-Mouse-and-Keyboard/
│
├── README.md                        ← This document
├── requirements.txt                 ← Python dependencies
├── haarcascade_frontalface_default.xml
├── model.yml
│
├── icons/                           ← Button images for the launcher GUI
│   ├── bot.png
│   ├── keyboard.png
│   ├── eye.jpeg
│   ├── hand.png
│   ├── exit.png
│   ├── man.jpeg
│   └── mn.png
│
├── MajorProject_Screenshots/        ← Demo screenshots
│
└── src/                             ← All Python source code
    ├── main.py                      ← Launcher GUI (Tkinter)
    ├── Gesture_Controller.py        ← Hand gesture → mouse + volume + brightness
    ├── eye.py                       ← Eye gaze → cursor + click + scroll + drag
    ├── samvk.py                     ← Virtual air keyboard
    ├── Proton.py                    ← Voice bot (Proton AI)
    ├── app.py                       ← eel server for chatbot UI
    ├── Gesture_Controller_Gloved.py ← Alternate: ArUco glove-based controller
    │
    ├── calib_images/                ← Camera calibration (for gloved controller)
    │   └── checkerboard/
    │
    └── web/                         ← Chatbot web UI (served by eel)
        ├── index.html
        ├── css/
        └── js/
```

---

## 12. Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: pycaw` | Package not installed | `pip install pycaw` |
| `ModuleNotFoundError: screen_brightness_control` | Package not installed | `pip install screen-brightness-control` |
| `ModuleNotFoundError: wikipedia` | Package not installed | `pip install wikipedia` |
| Camera opens but shows black screen | Another app is using the camera | Close Teams/Zoom/other webcam apps |
| Eye mode: cursor jitters wildly | Poor lighting or face not centred | Move to even lighting, face camera directly |
| Gesture mode: clicks fire accidentally | Hand too close or poor lighting | Move hand to 40–60 cm, improve lighting |
| VoiceBot: "Service is down" | No internet connection | Connect to internet (Google Speech API is online) |
| VoiceBot Chrome window doesn't open | Chrome not installed or `eel` issue | Install Chrome; or use `mode='default'` in `app.py` |
| Keyboard: keys not typing into app | Focus is on the webcam window | Click your target app (Notepad/browser) first, then use keyboard |
| Brightness control not working | Laptop using display driver without WMI | Try running as Administrator |
| `AudioDevice has no attribute Activate` | Old pycaw code with new pycaw version | Already fixed in current code |



*Built with MediaPipe · OpenCV · CVzone · PyAutoGUI · pyttsx3 · SpeechRecognition · eel*

