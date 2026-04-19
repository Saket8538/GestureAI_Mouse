import pyttsx3
import speech_recognition as sr
from datetime import date
import time
import webbrowser
import datetime
import re
from pynput.keyboard import Key, Controller
import pyautogui
import sys
import os
from os import listdir
from os.path import isfile, join
import wikipedia
from pycaw.pycaw import AudioUtilities
import Gesture_Controller
#import Gesture_Controller_Gloved as Gesture_Controller
import app
from threading import Thread
from mode_hub import hub, Mode
from config_loader import get
from logger import log
from ai_brain import AIBrain, AIBrainTransientError
from action_executor import execute_actions
from feedback import play_start_sound  # noqa: F401 – kept for future voice-start beep


def _get_volume():
    """Get system volume interface — works across all pycaw versions."""
    try:
        return AudioUtilities.GetSpeakers().EndpointVolume
    except AttributeError:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import IAudioEndpointVolume
        iface = AudioUtilities.GetSpeakers().Activate(
            IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return cast(iface, POINTER(IAudioEndpointVolume))


today = date.today()
r = sr.Recognizer()
keyboard = Controller()
engine = pyttsx3.init()
voices = engine.getProperty('voices')
# Use config for TTS settings
_tts_idx = get("voice.tts_voice_index", 1)
engine.setProperty('voice', voices[_tts_idx].id if len(voices) > _tts_idx else voices[0].id)
engine.setProperty('rate', get("voice.tts_rate", 150))
engine.setProperty('volume', get("voice.tts_volume", 1.0))
file_exp_status = False
files = []
path = ''
is_awake = True  # Bot status

# ── AI Brain (LLM-powered intent understanding) ─────────────────────────────
_ai_brain = AIBrain()

# ── Lookup tables used by the voice dispatcher ───────────────────────────────
# Keys are spoken/recognized text (all lowercase).
# Sorted longest-key-first in _open_anything() to avoid 'google' matching before 'google maps'.
SITE_MAP = {
    'google maps':         'https://maps.google.com',
    'google drive':        'https://drive.google.com',
    'google docs':         'https://docs.google.com',
    'google sheets':       'https://sheets.google.com',
    'google slides':       'https://slides.google.com',
    'google translate':    'https://translate.google.com',
    'google news':         'https://news.google.com',
    'google colab':        'https://colab.research.google.com',
    'youtube music':       'https://music.youtube.com',
    'amazon prime':        'https://www.primevideo.com',
    'microsoft teams':     'https://teams.microsoft.com',
    'stack overflow':      'https://stackoverflow.com',
    'khan academy':        'https://www.khanacademy.org',
    'online compiler':     'https://www.programiz.com/python-programming/online-compiler/',
    'python compiler':     'https://www.programiz.com/python-programming/online-compiler/',
    'java compiler':       'https://www.programiz.com/java-programming/online-compiler/',
    'google':              'https://www.google.com',
    'gmail':               'https://mail.google.com',
    'youtube':             'https://www.youtube.com',
    'facebook':            'https://www.facebook.com',
    'instagram':           'https://www.instagram.com',
    'twitter':             'https://www.twitter.com',
    'whatsapp':            'https://web.whatsapp.com',
    'netflix':             'https://www.netflix.com',
    'amazon':              'https://www.amazon.in',
    'flipkart':            'https://www.flipkart.com',
    'github':              'https://www.github.com',
    'stackoverflow':       'https://stackoverflow.com',
    'wikipedia':           'https://www.wikipedia.org',
    'spotify':             'https://open.spotify.com',
    'linkedin':            'https://www.linkedin.com',
    'reddit':              'https://www.reddit.com',
    'twitch':              'https://www.twitch.tv',
    'zoom':                'https://zoom.us',
    'teams':               'https://teams.microsoft.com',
    'outlook':             'https://outlook.live.com',
    'chatgpt':             'https://chat.openai.com',
    'openai':              'https://chat.openai.com',
    'gemini':              'https://gemini.google.com',
    'colab':               'https://colab.research.google.com',
    'kaggle':              'https://www.kaggle.com',
    'coursera':            'https://www.coursera.org',
    'udemy':               'https://www.udemy.com',
    'replit':              'https://replit.com',
    'canva':               'https://www.canva.com',
    'figma':               'https://www.figma.com',
    'maps':                'https://maps.google.com',
    'news':                'https://news.google.com',
    'translate':           'https://translate.google.com',
    'music':               'https://music.youtube.com',
    'browser':             'https://www.google.com',
    'weather':             'https://www.google.com/search?q=weather+today',
}

APP_MAP = {
    'file explorer':  'explorer',
    'task manager':   'taskmgr',
    'control panel':  'control',
    'command prompt': 'cmd',
    'powershell':     'powershell',
    'ms paint':       'mspaint',
    'notepad':        'notepad',
    'calculator':     'calc',
    'paint':          'mspaint',
    'word':           'winword',
    'excel':          'excel',
    'powerpoint':     'powerpnt',
    'explorer':       'explorer',
    'calc':           'calc',
    'cmd':            'cmd',
    'camera':         'microsoft.windows.camera:',
    'settings':       'ms-settings:',
    'snipping tool':  'snippingtool',
    'photos':         'ms-photos:',
    'clock':          'ms-clock:',
    'store':          'ms-windows-store:',
    'voice recorder': 'microsoft.windows.soundrecorder:',
    'screen recorder':'ms-screenclip:',
}


def _open_anything(name):
    """Open `name` as a Windows system app, known website, or inferred URL.
    Checks APP_MAP then SITE_MAP (both sorted longest-key-first to avoid short
    keys matching prematurely), then falls back to constructing a URL.
    """
    name = name.strip().lower()
    for key in sorted(APP_MAP.keys(), key=len, reverse=True):
        if key in name:
            os.system(f'start {APP_MAP[key]}')
            return key
    for key in sorted(SITE_MAP.keys(), key=len, reverse=True):
        if key in name:
            webbrowser.get().open(SITE_MAP[key])
            return key
    # Last resort: build URL from spoken name ("dot" → ".")
    url_name = name.replace(' dot ', '.').replace(' dot', '.').replace('dot ', '.')
    url_name = url_name.replace(' ', '')
    if '.' not in url_name:
        url_name += '.com'
    if not url_name.startswith('http'):
        url_name = 'https://' + url_name
    webbrowser.get().open(url_name)
    return name


def proton_chat():
    global is_awake
    last_mode_target = None
    _pending_confirmation = {"action": None, "expires_at": 0.0}

    def _cfg_bool(dotpath, default=False):
        """Parse booleans from YAML/env style values safely."""
        val = get(dotpath, default)
        if isinstance(val, bool):
            return val
        if isinstance(val, (int, float)):
            return bool(val)
        if isinstance(val, str):
            return val.strip().lower() in {"1", "true", "yes", "on"}
        return bool(default)

    def _cfg_int(dotpath, default=0):
        """Read integer config safely."""
        try:
            return int(get(dotpath, default))
        except (TypeError, ValueError):
            return int(default)

    _require_wake_word = _cfg_bool("voice.require_wake_word", False)
    _confirm_timeout_sec = _cfg_int("voice.confirmation_timeout", 30)
    _macro_max_steps = max(1, _cfg_int("voice.macro_max_steps", 4))
    
    def reply(audio):
        app.ChatBot.addAppMsg(audio)
        log.info("Proton: %s", audio)
        engine.say(audio)
        engine.runAndWait()


    def wish():
        hour = int(datetime.datetime.now().hour)
        if hour>=0 and hour<12:
            reply("Good Morning!")
        elif hour>=12 and hour<18:
            reply("Good Afternoon!")
        else:
            reply("Good Evening!")  
        reply("I am Proton, how may I help you?")

    # Set Microphone parameters
    with sr.Microphone() as source:
        r.dynamic_energy_threshold = True   # auto-adjust to room noise level
        try:
            r.pause_threshold = float(get("voice.pause_threshold", 1.0))
        except (TypeError, ValueError):
            r.pause_threshold = 1.0
        r.adjust_for_ambient_noise(source, duration=0.5)
    try:
        _phrase_limit = int(get("voice.phrase_time_limit", 15))
    except (TypeError, ValueError):
        _phrase_limit = 15

    def _normalize_voice_text(text):
        """Normalize noisy speech-recognition output into stable command text."""
        txt = (text or "").lower().strip()
        txt = re.sub(r"[^a-z0-9\s]", " ", txt)
        txt = re.sub(r"\s+", " ", txt).strip()

        replacements = {
            "i control": "eye control",
            "i tracking": "eye tracking",
            "i mode": "eye mode",
            "jester": "gesture",
            "gestor": "gesture",
            "key board": "keyboard",
            "virtual key board": "virtual keyboard",
            "start ai": "start eye",
            "stop ai": "stop eye",
        }
        for src, dst in replacements.items():
            txt = txt.replace(src, dst)
        return txt

    def _split_macro_commands(text):
        """Split a natural command into multiple sequential steps.

        Example: "open notepad and then type hello" ->
                 ["open notepad", "type hello"]
        """
        raw = (text or "").strip()
        if not raw:
            return []
        parts = re.split(r"\b(?:and then|after that|then|next)\b", raw)
        cmds = [p.strip(" ,") for p in parts if p and p.strip(" ,")]
        if len(cmds) <= 1:
            return [raw]
        return cmds[:_macro_max_steps]

    def _clear_confirmation():
        _pending_confirmation["action"] = None
        _pending_confirmation["expires_at"] = 0.0

    def _arm_confirmation(action, prompt):
        """Queue a risky action requiring explicit user confirmation."""
        _pending_confirmation["action"] = action
        _pending_confirmation["expires_at"] = time.time() + max(3, _confirm_timeout_sec)
        reply(f"{prompt} Please say confirm or cancel.")

    def _handle_pending_confirmation(voice_data):
        """Execute or cancel a pending risky action when user confirms."""
        action = _pending_confirmation["action"]
        if not action:
            return False

        if time.time() > _pending_confirmation["expires_at"]:
            _clear_confirmation()
            return False

        vd = voice_data.strip().lower()
        yes_kws = ["confirm", "yes", "ok", "okay", "proceed", "do it", "continue"]
        no_kws = ["cancel", "no", "stop", "never mind", "nevermind", "do not"]

        if any(k in vd for k in no_kws):
            _clear_confirmation()
            reply("Cancelled.")
            return True

        if any(k in vd for k in yes_kws):
            _clear_confirmation()
            if action == "lock_screen":
                import ctypes
                ctypes.windll.user32.LockWorkStation()
                reply("Locking screen")
                return True
            if action == "close_window":
                pyautogui.hotkey('alt', 'f4')
                reply("Closing window")
                return True
            if action == "exit_proton":
                for mode in [Mode.EYE, Mode.GESTURE, Mode.KEYBOARD]:
                    hub.stop(mode)
                Gesture_Controller.GestureController.gc_mode = 0
                app.ChatBot.close()
                sys.exit()
            return True

        return False

# Audio to String
    def record_audio():
        with sr.Microphone() as source:
            voice_data = ''
            audio = r.listen(source, phrase_time_limit=_phrase_limit)

            try:
                voice_data = r.recognize_google(audio)
            except sr.RequestError:
                reply('Sorry my Service is down. Plz check your Internet connection')
            except sr.UnknownValueError:
                log.debug("Speech not recognized")
                pass
            return voice_data.lower()

    # ── AI Brain dispatcher ──────────────────────────────────────────────────
    def _try_ai_brain(voice_data):
        """Attempt LLM interpretation. Returns True if handled, False to fall through."""
        global is_awake
        if not _ai_brain.available:
            return False

        try:
            result = _ai_brain.interpret(voice_data)
        except AIBrainTransientError:
            reply("AI service is busy right now. Please try again in a moment.")
            return True   # handled — do NOT fall through to Google search

        if result is None:
            return False

        actions = result.get("actions", [])
        ai_reply = result.get("reply", "")

        if not actions and not ai_reply:
            return False

        # Handle special actions that need Proton-level state
        for act in actions:
            if act.get("type") == "sleep":
                reply(ai_reply or "Goodbye! Say Proton wake up when you need me!")
                is_awake = False
                return True
            if act.get("type") == "exit":
                for mode in [Mode.EYE, Mode.GESTURE, Mode.KEYBOARD]:
                    hub.stop(mode)
                Gesture_Controller.GestureController.gc_mode = 0
                reply(ai_reply or "Shutting down. Goodbye!")
                app.ChatBot.close()
                return True

        # Execute actions via the sandboxed executor
        mode_ref = (hub, Mode)
        override = execute_actions(actions, reply, mode_ref)

        # Speak the reply
        final_reply = override or ai_reply
        if final_reply:
            reply(final_reply)

        return True

    # ── Camera conflict resolution ───────────────────────────────────────────
    _CAM_MODE_KEYS = {
        Mode.EYE: 'eye.camera_index',
        Mode.GESTURE: 'gesture.camera_index',
        Mode.KEYBOARD: 'keyboard.camera_index',
    }

    def _stop_camera_conflicts(new_mode):
        """Stop other camera modes sharing the same device and wait for camera release."""
        if new_mode not in _CAM_MODE_KEYS:
            return
        new_cam = get(_CAM_MODE_KEYS[new_mode], 0)
        stopped_any = False
        for mode, cam_key in _CAM_MODE_KEYS.items():
            if mode != new_mode and hub.is_active(mode):
                if get(cam_key, 0) == new_cam:
                    hub.stop(mode)
                    if mode == Mode.GESTURE:
                        Gesture_Controller.GestureController.gc_mode = 0
                    log.info("Auto-stopped %s (camera conflict)", mode.name)
                    reply(f'Auto-stopped {mode.name.lower()} (camera in use)')
                    stopped_any = True
        # Give the stopped mode time to release the camera device
        if stopped_any:
            time.sleep(1.5)

    def _launch_mode(mode):
        """Launch a mode with camera conflict resolution and error handling."""
        _stop_camera_conflicts(mode)
        hub.start(mode)
        try:
            if mode == Mode.EYE:
                from eye import eye_move
                Thread(target=eye_move, daemon=True).start()
                reply('Eye control launched')
            elif mode == Mode.GESTURE:
                Thread(target=Gesture_Controller.gest_control, daemon=True).start()
                reply('Gesture control launched')
            elif mode == Mode.KEYBOARD:
                from samvk import vk_keyboard
                Thread(target=vk_keyboard, daemon=True).start()
                reply('Virtual keyboard launched')
        except Exception as e:
            hub.stop(mode)
            log.error("Failed to launch %s: %s", mode.name, e)
            reply(f'Failed to launch {mode.name.lower()}')

    def _stop_mode(mode):
        """Stop a mode safely with feedback."""
        labels = {
            Mode.EYE: "Eye control",
            Mode.GESTURE: "Gesture control",
            Mode.KEYBOARD: "Virtual keyboard",
        }
        label = labels.get(mode, mode.name.capitalize())
        if hub.is_active(mode):
            hub.stop(mode)
            if mode == Mode.GESTURE:
                Gesture_Controller.GestureController.gc_mode = 0
            # Give the mode's thread time to release camera / resources
            time.sleep(0.5)
            reply(f'{label} stopped')
        else:
            reply(f'{label} is already inactive')

    # ── Mode switching (smart matching for voice + text) ─────────────────────
    def _handle_mode_switch(voice_data):
        """Detect and handle mode-switch commands. Returns True if handled.

        Supports:
        - Text shortcuts: type just "eye", "gesture", "keyboard" to toggle
        - Voice commands: "start eye control", "stop gesture", etc.
        - Common speech errors: "I control" → eye, "jester" → gesture
        - Camera conflict auto-resolution between modes sharing a camera
        """
        nonlocal last_mode_target
        vd = voice_data.lower().strip()

        # ── Autonomous presets for one-shot setup ───────────────────────
        if any(k in vd for k in ['hands free mode', 'handsfree mode', 'reading mode']):
            _stop_mode(Mode.GESTURE)
            _stop_mode(Mode.KEYBOARD)
            if not hub.is_active(Mode.EYE):
                _launch_mode(Mode.EYE)
            else:
                reply('Hands-free mode already active')
            last_mode_target = Mode.EYE
            return True

        if any(k in vd for k in ['typing mode', 'text mode', 'writer mode']):
            _stop_mode(Mode.GESTURE)
            _stop_mode(Mode.EYE)
            if not hub.is_active(Mode.KEYBOARD):
                _launch_mode(Mode.KEYBOARD)
            else:
                reply('Typing mode already active')
            last_mode_target = Mode.KEYBOARD
            return True

        if any(k in vd for k in ['presentation mode', 'present mode', 'demo mode']):
            _stop_mode(Mode.EYE)
            _stop_mode(Mode.KEYBOARD)
            if not hub.is_active(Mode.GESTURE):
                _launch_mode(Mode.GESTURE)
            else:
                reply('Presentation mode already active')
            last_mode_target = Mode.GESTURE
            return True

        # ── Quick text/voice toggles (exact-match shortcuts) ─────────────
        _TOGGLE_MAP = {
            'eye': Mode.EYE, 'eyes': Mode.EYE,
            'eye control': Mode.EYE, 'eye mode': Mode.EYE,
            'eye tracking': Mode.EYE, 'eye mouse': Mode.EYE,
            'iris': Mode.EYE, 'iris control': Mode.EYE,
            'gaze': Mode.EYE, 'gaze control': Mode.EYE,
            'gesture': Mode.GESTURE, 'gestures': Mode.GESTURE,
            'gesture control': Mode.GESTURE, 'gesture mode': Mode.GESTURE,
            'hand control': Mode.GESTURE, 'hand gesture': Mode.GESTURE,
            'gesture mouse': Mode.GESTURE,
            'keyboard': Mode.KEYBOARD,
            'virtual keyboard': Mode.KEYBOARD, 'keyboard mode': Mode.KEYBOARD,
            'air keyboard': Mode.KEYBOARD, 'keyboard control': Mode.KEYBOARD,
            'voice': Mode.VOICE, 'voice control': Mode.VOICE,
            'voice mode': Mode.VOICE, 'voice assistant': Mode.VOICE,
            'proton': Mode.VOICE,
        }
        if vd in _TOGGLE_MAP:
            mode = _TOGGLE_MAP[vd]
            if mode == Mode.VOICE:
                reply('Voice control is already running — you are using it right now!')
                last_mode_target = mode
                return True
            if hub.is_active(mode):
                _stop_mode(mode)
            else:
                _launch_mode(mode)
            last_mode_target = mode
            return True

        # ── Stop all ─────────────────────────────────────────────────────
        _STOP_ALL = ['stop all', 'stop everything', 'disable all',
                     'close all modes', 'turn off all', 'shut down all',
                     'kill all modes', 'end all', 'close all']
        if any(w in vd for w in _STOP_ALL):
            for mode in [Mode.EYE, Mode.GESTURE, Mode.KEYBOARD]:
                hub.stop(mode)
            Gesture_Controller.GestureController.gc_mode = 0
            last_mode_target = None
            reply('All input modes stopped')
            return True

        # ── Status query ─────────────────────────────────────────────────
        _STATUS = ['what modes', 'active modes', 'which modes', 'mode status',
                   'current modes', 'list modes', 'what is active',
                   'what is running', 'show modes']
        if any(w in vd for w in _STATUS):
            active = hub.active_modes()
            if active:
                names = ', '.join(m.name.lower() for m in active)
                reply(f'Active modes: {names}')
            else:
                reply('No input modes are currently active')
            return True

        # ── Word-level signal detection ──────────────────────────────────
        # Catches mode-switch intent even with speech recognition errors
        words = set(vd.split())
        stop_signals = {'stop', 'disable', 'deactivate', 'close', 'end',
                'kill', 'shut', 'off', 'quit'}
        start_signals = {'start', 'enable', 'activate', 'launch', 'begin',
                 'open', 'switch', 'on', 'run'}

        # Detect which mode is referenced
        mode_target = None

        # Eye: "eye", "eyes", "iris", "gaze"
        # Also "I control" / "I tracking" (common "eye" misrecognition)
        eye_direct = {'eye', 'eyes', 'iris', 'gaze'}
        eye_context = {'control', 'tracking', 'mouse', 'mode', 'cursor',
                       'movement', 'move'}
        if words & eye_direct:
            mode_target = Mode.EYE
        elif 'i' in words and (words & eye_context):
            mode_target = Mode.EYE

        # Gesture: "gesture", "jester" (misrecognition), "hand"
        gesture_direct = {'gesture', 'gestures', 'jester'}
        gesture_context = {'control', 'mode', 'mouse', 'recognition'}
        if mode_target is None:
            if words & gesture_direct:
                mode_target = Mode.GESTURE
            elif 'hand' in words and (words & gesture_context):
                mode_target = Mode.GESTURE

        # Keyboard: "keyboard", "keypad", "key board"
        keyboard_direct = {'keyboard', 'keypad'}
        if mode_target is None:
            if words & keyboard_direct:
                mode_target = Mode.KEYBOARD
            elif 'key' in words and 'board' in words:
                mode_target = Mode.KEYBOARD
            elif 'virtual' in words and 'keyboard' in vd:
                mode_target = Mode.KEYBOARD

        # Voice: "voice", "voice control", "proton"
        voice_direct = {'voice', 'voicebot', 'proton'}
        voice_context = {'control', 'mode', 'assistant'}
        if mode_target is None:
            if words & voice_direct:
                mode_target = Mode.VOICE

        # Pronoun resolution: "stop it", "start that" uses last referenced mode.
        if mode_target is None and last_mode_target is not None:
            if ('it' in words or 'that' in words) and (words & (stop_signals | start_signals | {'toggle'})):
                mode_target = last_mode_target

        if mode_target is None:
            return False

        wants_stop = bool(words & stop_signals)
        wants_start = bool(words & start_signals)

        # "turn on" vs "turn off"
        if 'turn' in words:
            wants_stop = 'off' in words
            wants_start = 'on' in words

        # "switch to X" = start
        if 'switch' in words and 'to' in words:
            wants_start, wants_stop = True, False

        # Both or neither → toggle
        # Voice mode: already running by definition (user is speaking)
        if mode_target == Mode.VOICE:
            if wants_stop:
                reply('To stop voice control, say goodbye or exit.')
            else:
                reply('Voice control is already running — you are using it right now!')
            last_mode_target = mode_target
            return True

        if wants_start == wants_stop:
            if hub.is_active(mode_target):
                _stop_mode(mode_target)
            else:
                _launch_mode(mode_target)
        elif wants_stop:
            _stop_mode(mode_target)
        else:
            if hub.is_active(mode_target):
                labels = {
                    Mode.EYE: "Eye control",
                    Mode.GESTURE: "Gesture control",
                    Mode.KEYBOARD: "Virtual keyboard",
                }
                reply(f"{labels.get(mode_target, mode_target.name.capitalize())} is already active")
            else:
                _launch_mode(mode_target)
        last_mode_target = mode_target
        return True

# ── Executes Commands: intent-based dispatcher (like Alexa) ──────────────
    def respond(voice_data):
        global file_exp_status, files, is_awake, path
        log.info("Voice input: %s", voice_data)
        app.eel.addUserMsg((voice_data or '').strip())
        voice_data = _normalize_voice_text((voice_data or '').replace('proton', ' ').strip())

        # ── 0. Wake guard ─────────────────────────────────────────────────────
        if not is_awake:
            if 'wake up' in voice_data or 'wakeup' in voice_data:
                is_awake = True
                wish()
            return

        # If a risky action is pending, handle confirm/cancel first.
        if _handle_pending_confirmation(voice_data):
            return

        # ── 1. File-browser intercept (open N / back) ─────────────────────────
        if file_exp_status:
            words = voice_data.split()
            has_number = any(w.isdigit() for w in words)
            if has_number and any(w in voice_data for w in ['open', 'select']):
                try:
                    idx = int([w for w in words if w.isdigit()][-1]) - 1
                    target = files[idx]
                    if isfile(join(path, target)):
                        os.startfile(os.path.join(path, target))
                        file_exp_status = False
                        reply(f'Opened {target}')
                    else:
                        path = os.path.join(path, target)
                        files = listdir(path)
                        filestr = ''.join(f'{i+1}:  {f}<br>' for i, f in enumerate(files))
                        reply('Opened folder')
                        app.ChatBot.addAppMsg(filestr)
                except Exception:
                    reply('I could not find that item. Please say the file number.')
                return
            elif 'back' in voice_data:
                parent = os.path.dirname(path.rstrip(os.sep))
                if not parent or parent == path:
                    reply('This is already the root directory.')
                else:
                    path = parent
                    files = listdir(path)
                    filestr = ''.join(f'{i+1}:  {f}<br>' for i, f in enumerate(files))
                    reply('Going back')
                    app.ChatBot.addAppMsg(filestr)
                return
            # else: not a file-nav command — fall through to main handler

        # ── 1.5. Mode switching (runs BEFORE keywords — never misrouted) ──────
        if _handle_mode_switch(voice_data):
            return

        # ── 2. Main intent dispatch (keyword matching) ────────────────────────

        # ·· Greetings / Identity ················································
        if any(w in voice_data for w in ['hello', ' hi ', 'hey', 'good morning',
                                          'good afternoon', 'good evening']):
            wish()

        elif any(w in voice_data for w in ['your name', 'who are you',
                                            'what are you', 'introduce yourself']):
            reply('My name is Proton! I am your personal voice assistant. '
                  'I can control your computer, browse the web, and much more.')

        elif any(w in voice_data for w in ['how are you', 'are you fine',
                                            "what's up", 'how do you do']):
            reply('I am doing great and ready to help!')

        elif any(w in voice_data for w in ['thank you', 'thanks']):
            reply("You're welcome! Always here to help.")

        elif 'date' in voice_data:
            reply(today.strftime("%B %d, %Y"))

        elif 'time' in voice_data:
            reply(str(datetime.datetime.now()).split(' ')[1].split('.')[0])

        # ·· Play / YouTube (checked before 'open') ······························
        elif 'play' in voice_data and 'youtube' in voice_data:
            query = (voice_data.replace('play', '').replace('on youtube', '')
                     .replace('youtube', '').replace('on', '').strip())
            url = f'https://www.youtube.com/results?search_query={query.replace(" ", "+")}'
            webbrowser.get().open(url)
            reply(f'Playing {query} on YouTube')

        elif any(w in voice_data for w in ['play music', 'play songs', 'open music',
                                            'play song', 'open youtube music']):
            webbrowser.get().open('https://music.youtube.com')
            reply('Opening YouTube Music')

        elif 'play' in voice_data:
            query = voice_data.replace('play', '').strip()
            url = f'https://www.youtube.com/results?search_query={query.replace(" ", "+")}'
            webbrowser.get().open(url)
            reply(f'Searching YouTube for {query}')

        # ·· Maps / Navigation ···················································
        elif any(w in voice_data for w in ['navigate to ', 'directions to ',
                                            'how to reach ', 'route to ', 'take me to ']):
            trigger = next(w for w in ['navigate to ', 'directions to ', 'how to reach ',
                                        'route to ', 'take me to '] if w in voice_data)
            place = voice_data.split(trigger, 1)[1].strip()
            webbrowser.get().open(
                f'https://www.google.com/maps/dir/?api=1&destination={place.replace(" ", "+")}')
            reply(f'Getting directions to {place}')

        elif any(w in voice_data for w in ['where is ', 'show me ', 'find on map',
                                            'open google maps', 'open maps']):
            place = ''
            for kw in ['where is ', 'show me ']:
                if kw in voice_data:
                    place = voice_data.split(kw, 1)[1].strip()
                    break
            url = (f'https://www.google.com/maps/search/{place.replace(" ", "+")}'
                   if place else 'https://maps.google.com')
            webbrowser.get().open(url)
            reply(f'Opening Maps{" for " + place if place else ""}')

        # ·· Weather ·············································ø···············
        elif 'weather' in voice_data:
            query = (voice_data.replace('weather', '').replace(' in ', '')
                     .replace(' at ', '').replace('today', '').strip())
            url = (f'https://www.google.com/search?q=weather+{query.replace(" ", "+")}'
                   if query else 'https://www.google.com/search?q=weather+today')
            webbrowser.get().open(url)
            reply(f'Checking weather{" for " + query if query else ""}')

        # ·· News ················································ø···············
        elif any(w in voice_data for w in ['news', 'headlines', 'latest news']):
            query = (voice_data.replace('news', '').replace('headlines', '')
                     .replace('latest', '').strip())
            url = (f'https://news.google.com/search?q={query.replace(" ", "+")}'
                   if query else 'https://news.google.com')
            webbrowser.get().open(url)
            reply('Opening news')

        # ·· Translate ···········································ø···············
        elif 'translate' in voice_data:
            query = voice_data.replace('translate', '').strip()
            url = (f'https://translate.google.com/?text={query.replace(" ", "%20")}'
                   if query else 'https://translate.google.com')
            webbrowser.get().open(url)
            reply(f'Opening Google Translate{": " + query if query else ""}')

        # ·· Wikipedia ···········································ø···············
        elif 'wikipedia' in voice_data:
            topic = voice_data.replace('wikipedia', '').strip()
            if not topic:
                reply('Please say a topic after wikipedia.')
            else:
                try:
                    result = wikipedia.summary(topic, sentences=2)
                    reply(result)
                except wikipedia.exceptions.DisambiguationError as e:
                    reply(f'That is a broad topic. Did you mean: {e.options[0]}?')
                except Exception:
                    webbrowser.get().open(
                        f'https://en.wikipedia.org/wiki/{topic.replace(" ", "_")}')
                    reply(f'Opening Wikipedia for {topic}')

        # ·· Online compiler ·····················································
        elif any(w in voice_data for w in ['online compiler', 'online python',
                                            'online java', 'online c', 'run code online',
                                            'replit', 'colab']):
            if 'python' in voice_data:
                url, lang = ('https://www.programiz.com/python-programming/online-compiler/',
                             'Python')
            elif 'java' in voice_data and 'javascript' not in voice_data:
                url, lang = ('https://www.programiz.com/java-programming/online-compiler/',
                             'Java')
            elif 'c++' in voice_data or 'cpp' in voice_data:
                url, lang = ('https://www.programiz.com/cpp-programming/online-compiler/',
                             'C++')
            elif 'replit' in voice_data:
                url, lang = 'https://replit.com', 'Replit'
            elif 'colab' in voice_data:
                url, lang = 'https://colab.research.google.com', 'Google Colab'
            else:
                url, lang = ('https://www.programiz.com/python-programming/online-compiler/',
                             'Python')
            webbrowser.get().open(url)
            reply(f'Opening {lang} online compiler')
        # ·· Search specific sites (Amazon, Flipkart, eBay) ·························
        elif 'search' in voice_data and any(
                site in voice_data for site in ['amazon', 'flipkart', 'ebay']):
            query = voice_data
            url = ''
            if 'amazon' in voice_data:
                for kw in ['search amazon for ', 'search on amazon for ',
                           'search on amazon ', 'search amazon ']:
                    if kw in voice_data:
                        query = voice_data.split(kw, 1)[1].strip()
                        break
                url = f'https://www.amazon.in/s?k={query.replace(" ", "+")}'
                reply(f'Searching Amazon for {query}')
            elif 'flipkart' in voice_data:
                for kw in ['search flipkart for ', 'search on flipkart for ',
                           'search on flipkart ', 'search flipkart ']:
                    if kw in voice_data:
                        query = voice_data.split(kw, 1)[1].strip()
                        break
                url = f'https://www.flipkart.com/search?q={query.replace(" ", "+")}'
                reply(f'Searching Flipkart for {query}')
            elif 'ebay' in voice_data:
                for kw in ['search ebay for ', 'search on ebay for ',
                           'search on ebay ', 'search ebay ']:
                    if kw in voice_data:
                        query = voice_data.split(kw, 1)[1].strip()
                        break
                url = f'https://www.ebay.com/sch/i.html?_nkw={query.replace(" ", "+")}'
                reply(f'Searching eBay for {query}')
            if url:
                webbrowser.get().open(url)
        # ·· Search Google ·······················································
        elif ('search' in voice_data or
              'google' in voice_data and 'open' not in voice_data):
            query = voice_data
            for kw in ['search for ', 'search ', 'google for ', 'google ']:
                if kw in voice_data:
                    query = voice_data.split(kw, 1)[1].strip()
                    break
            url = f'https://www.google.com/search?q={query.replace(" ", "+")}'
            webbrowser.get().open(url)
            reply(f'Searching for {query}')

        # ·· Location (two-step) ·················································
        elif 'location' in voice_data or 'find place' in voice_data:
            reply('Which place are you looking for?')
            temp_audio = record_audio()
            if temp_audio:
                app.eel.addUserMsg(temp_audio)
                webbrowser.get().open(
                    f'https://www.google.com/maps/search/{temp_audio.replace(" ", "+")}')
                reply('This is what I found')

        # ·· Screenshot ··········································ø···············
        elif any(w in voice_data for w in ['screenshot', 'capture screen',
                                            'take screenshot', 'print screen']):
            pyautogui.hotkey('win', 'prtsc')
            reply('Screenshot saved to your Pictures folder')

        # ·· Type into active window ·············································
        elif 'type ' in voice_data or voice_data.strip().startswith('type'):
            text_to_type = voice_data
            for kw in ['type out ', 'type in ', 'type ']:
                if kw in voice_data:
                    text_to_type = voice_data.split(kw, 1)[1].strip()
                    break
            if text_to_type and text_to_type != voice_data:
                time.sleep(0.3)
                pyautogui.write(text_to_type, interval=0.06)
                reply(f'Typed: {text_to_type}')
            else:
                reply('Please say what to type. Example: proton type hello world')

        # ·· Mouse controls ······················································
        elif 'double click' in voice_data:
            pyautogui.doubleClick()
            reply('Double clicked')

        elif 'right click' in voice_data:
            pyautogui.rightClick()
            reply('Right clicked')

        elif voice_data.strip() in ['click', 'left click', 'mouse click', 'click here']:
            pyautogui.click()
            reply('Clicked')

        elif any(w in voice_data for w in ['scroll up', 'page up', 'move up',
                                            'scroll top']):
            pyautogui.scroll(5)
            reply('Scrolled up')

        elif any(w in voice_data for w in ['scroll down', 'page down', 'move down',
                                            'scroll bottom']):
            pyautogui.scroll(-5)
            reply('Scrolled down')

        # ·· Key presses ·········································ø···············
        elif any(w in voice_data for w in ['press enter', 'hit enter', 'enter key',
                                            'press return']):
            pyautogui.press('enter')
            reply('Enter pressed')

        elif any(w in voice_data for w in ['press tab', 'tab key', 'next field']):
            pyautogui.press('tab')
            reply('Tab pressed')

        elif any(w in voice_data for w in ['press escape', 'press esc', 'escape key']):
            pyautogui.press('escape')
            reply('Escape pressed')

        elif any(w in voice_data for w in ['press space', 'space bar', 'press spacebar']):
            pyautogui.press('space')
            reply('Space pressed')

        elif any(w in voice_data for w in ['press delete', 'delete key']):
            pyautogui.press('delete')
            reply('Delete pressed')

        # ·· Keyboard shortcuts ··················································
        elif any(w in voice_data for w in ['select all', 'ctrl a']):
            pyautogui.hotkey('ctrl', 'a')
            reply('Selected all')

        elif any(w in voice_data for w in ['undo', 'ctrl z']):
            pyautogui.hotkey('ctrl', 'z')
            reply('Undo')

        elif any(w in voice_data for w in ['redo', 'ctrl y']):
            pyautogui.hotkey('ctrl', 'y')
            reply('Redo')

        elif any(w in voice_data for w in ['save file', 'save this', 'ctrl s']):
            pyautogui.hotkey('ctrl', 's')
            reply('Saved')

        elif any(w in voice_data for w in ['new tab', 'open new tab', 'open tab']):
            pyautogui.hotkey('ctrl', 't')
            reply('Opened new tab')

        elif any(w in voice_data for w in ['close tab', 'shut tab']):
            pyautogui.hotkey('ctrl', 'w')
            reply('Closed tab')

        elif any(w in voice_data for w in ['go back', 'browser back', 'previous page',
                                            'back page']):
            pyautogui.hotkey('alt', 'left')
            reply('Going back')

        elif any(w in voice_data for w in ['go forward', 'browser forward', 'next page']):
            pyautogui.hotkey('alt', 'right')
            reply('Going forward')

        elif any(w in voice_data for w in ['zoom in', 'make bigger']):
            pyautogui.hotkey('ctrl', '+')
            reply('Zoomed in')

        elif any(w in voice_data for w in ['zoom out', 'make smaller']):
            pyautogui.hotkey('ctrl', '-')
            reply('Zoomed out')

        elif any(w in voice_data for w in ['minimize', 'minimise', 'hide window']):
            pyautogui.hotkey('win', 'down')
            reply('Window minimized')

        elif any(w in voice_data for w in ['maximize', 'maximise', 'full screen',
                                            'make fullscreen']):
            pyautogui.hotkey('win', 'up')
            reply('Window maximized')

        elif any(w in voice_data for w in ['close window', 'close app', 'close this',
                                            'close application']):
            _arm_confirmation('close_window', 'I am ready to close the current window.')

        elif any(w in voice_data for w in ['copy', 'ctrl c', 'copy that']):
            with keyboard.pressed(Key.ctrl):
                keyboard.press('c')
                keyboard.release('c')
            reply('Copied')

        elif any(w in voice_data for w in ['paste', 'ctrl v', 'paste that', 'pest', 'page']):
            with keyboard.pressed(Key.ctrl):
                keyboard.press('v')
                keyboard.release('v')
            reply('Pasted')

        elif any(w in voice_data for w in ['refresh', 'reload', 'ctrl r']):
            pyautogui.hotkey('ctrl', 'r')
            reply('Page refreshed')

        # ·· Volume / Audio ······················································
        elif any(w in voice_data for w in ['volume up', 'increase volume',
                                            'louder', 'turn up']):
            vol = _get_volume()
            vol.SetMasterVolumeLevelScalar(
                min(vol.GetMasterVolumeLevelScalar() + 0.10, 1.0), None)
            reply('Volume increased')

        elif any(w in voice_data for w in ['volume down', 'decrease volume',
                                            'quieter', 'lower volume', 'turn down']):
            vol = _get_volume()
            vol.SetMasterVolumeLevelScalar(
                max(vol.GetMasterVolumeLevelScalar() - 0.10, 0.0), None)
            reply('Volume decreased')

        elif any(w in voice_data for w in ['unmute', 'turn sound on', 'unsilence']):
            _get_volume().SetMute(0, None)
            reply('Unmuted')

        elif any(w in voice_data for w in ['mute', 'silence', 'turn sound off']):
            _get_volume().SetMute(1, None)
            reply('Muted')

        # ·· Brightness ··························································
        elif any(w in voice_data for w in ['brightness up', 'increase brightness',
                                            'brighter', 'screen brighter']):
            import screen_brightness_control as sbc
            current = sbc.get_brightness(display=0)[0]
            sbc.set_brightness(min(current + 10, 100))
            reply('Brightness increased')

        elif any(w in voice_data for w in ['brightness down', 'decrease brightness',
                                            'dimmer', 'darker', 'screen dimmer']):
            import screen_brightness_control as sbc
            current = sbc.get_brightness(display=0)[0]
            sbc.set_brightness(max(current - 10, 0))
            reply('Brightness decreased')

        # ·· Camera ····························································
        elif any(w in voice_data for w in ['take photo', 'take picture', 'take selfie',
                                            'capture photo', 'open camera',
                                            'start camera', 'launch camera']):
            os.system('start microsoft.windows.camera:')
            reply('Opening camera')

        # ·· Lock / Switch / Desktop ···········································
        elif any(w in voice_data for w in ['lock screen', 'lock computer', 'lock pc',
                                            'lock my computer']):
            _arm_confirmation('lock_screen', 'I am ready to lock your screen.')

        elif any(w in voice_data for w in ['switch window', 'alt tab', 'next window',
                                            'change window']):
            pyautogui.hotkey('alt', 'tab')
            reply('Switching window')

        elif any(w in voice_data for w in ['show desktop', 'minimize all',
                                            'go to desktop']):
            pyautogui.hotkey('win', 'd')
            reply('Showing desktop')

        # ·· Select text (voice-driven text selection for accessibility) ·······
        elif any(w in voice_data for w in ['start selecting', 'select text',
                                            'begin selection']):
            pyautogui.mouseDown()
            reply('Selection started — say stop selecting when done')

        elif any(w in voice_data for w in ['stop selecting', 'end selection',
                                            'finish selection']):
            pyautogui.mouseUp()
            reply('Selection ended')

        # ·· Read clipboard ······················································
        elif any(w in voice_data for w in ['read clipboard', 'what did i copy',
                                            'read what i copied']):
            import subprocess
            result = subprocess.run(
                ['powershell', '-command', 'Get-Clipboard'],
                capture_output=True, text=True, timeout=5)
            clip = result.stdout.strip()
            reply(f'Your clipboard says: {clip}' if clip else 'Clipboard is empty')

        # ·· Help ·······························································
        elif any(w in voice_data for w in ['what can you do', 'help me', 'show commands',
                                            'list commands', 'your features']):
            reply('I can: open apps and websites, search Google or Amazon or Flipkart, '
                  'play YouTube, navigate on Maps, check weather, read news, translate, '
                  'Wikipedia lookup, type text, click, scroll, volume and brightness '
                  'control, take screenshots, lock screen, switch windows, select text, '
                  'copy, paste, save, undo, redo. '
                  'Mode switching: just say or type eye, gesture, or keyboard to toggle. '
                  'Or say start eye, stop gesture, switch to keyboard, turn on gesture, '
                  'enable eye, and many more. Say stop all to disable all modes. '
                'Say active modes to check what is running. '
                'Autonomous presets: hands free mode, typing mode, presentation mode. '
                'You can chain tasks: open notepad and then type hello. '
                'For safety, risky actions ask for confirm or cancel.')

        # ·· GENERIC OPEN — handles any app, website, or service name ··········
        elif any(w in voice_data for w in ['open ', 'launch ', 'start ']):
            name = voice_data
            for kw in ['open ', 'launch ', 'start ']:
                if kw in voice_data:
                    name = voice_data.split(kw, 1)[1].strip()
                    break
            # Guard: if the extracted name is really a mode keyword, reroute
            _mode_words = {'eye', 'eyes', 'iris', 'gaze', 'gesture', 'gestures',
                           'hand', 'keyboard', 'keypad', 'voice', 'proton'}
            if name and set(name.split()) & _mode_words:
                if _handle_mode_switch(voice_data):
                    return
            if name:
                try:
                    opened = _open_anything(name)
                    reply(f'Opening {opened}')
                except Exception:
                    reply(f"Sorry, I could not open {name}. Please check your internet.")
            else:
                reply("What would you like me to open?")

        # ·· Go to URL ···························································
        elif 'go to ' in voice_data:
            site = voice_data.split('go to ', 1)[1].strip()
            site = site.replace(' dot ', '.').replace(' dot', '.').replace('dot ', '.')
            site = site.replace(' ', '')
            if '.' not in site:
                site += '.com'
            if not site.startswith('http'):
                site = 'https://' + site
            webbrowser.get().open(site)
            reply(f'Opening {site}')

        # ·· List files ··················································ø·······
        elif (any(w in voice_data for w in ['list files', 'list directory',
                                             'show files', 'show directory'])
              or voice_data.strip() == 'list'):
            path = 'C:\\'
            files = listdir(path)
            filestr = ''.join(f'{i+1}:  {f}<br>' for i, f in enumerate(files))
            file_exp_status = True
            reply('These are the files in your root directory')
            app.ChatBot.addAppMsg(filestr)

        # ·· Jokes ·······················································ø·······
        elif any(w in voice_data for w in ['joke', 'tell me a joke', 'make me laugh',
                                            'something funny', 'funny']):
            import random
            jokes = [
                "Why do programmers prefer dark mode? Because light attracts bugs!",
                "Why did the computer go to the doctor? Because it had a virus!",
                "How many programmers does it take to change a light bulb? "
                "None — it's a hardware problem.",
                "I told my computer I needed a break. Now it won't stop sending me "
                "vacation ads.",
                "Why do Java developers wear glasses? Because they don't C sharp!",
            ]
            reply(random.choice(jokes))

        # ·· Sleep ·······················································ø·······
        elif any(w in voice_data for w in ['sleep', 'go to sleep', 'take a break',
                                            'good bye', 'goodbye', 'bye']):
            reply("Goodbye! Say 'Proton wake up' when you need me!")
            is_awake = False

        # ·· Exit ································································
        elif any(w in voice_data for w in ['exit', 'terminate', 'shut down proton',
                                            'close proton', 'quit proton']):
            _arm_confirmation('exit_proton', 'I am ready to close Proton completely.')

        # ·· SMART FALLBACK: AI Brain → Google search ····························
        else:
            if voice_data.strip():
                # Guard: catch any stray mode-switch phrasing before searching
                _fallback_mode_words = {'eye', 'eyes', 'gesture', 'gestures',
                                        'keyboard', 'voice', 'proton'}
                _fallback_action_words = {'start', 'stop', 'switch', 'enable',
                                          'disable', 'activate', 'launch', 'toggle',
                                          'turn', 'open', 'close', 'run'}
                _fb_words = set(voice_data.split())
                if (_fb_words & _fallback_mode_words) and (_fb_words & _fallback_action_words):
                    if _handle_mode_switch(voice_data):
                        return
                # Try AI Brain for complex/novel commands
                if _ai_brain.available and _try_ai_brain(voice_data):
                    log.debug("Fallback to AI Brain: %s", voice_data)
                    return
                # Last resort: Google search
                search_url = ('https://www.google.com/search?q='
                              + voice_data.strip().replace(' ', '+'))
                try:
                    webbrowser.get().open(search_url)
                    reply(f"I searched Google for: {voice_data.strip()}")
                except Exception:
                    reply("Sorry, I could not process that command. "
                          "Please try rephrasing.")

# ------------------Driver Code--------------------

    log.info("Proton voice assistant starting...")
    hub.start(Mode.VOICE)

    # Only start a new ChatBot server if one isn't already running.
    # Re-launching eel on the same port causes OSError 10048.
    if not app.ChatBot.started:
        t1 = Thread(target = app.ChatBot.start)
        t1.start()

# Lock main thread until Chatbot has started
        while not app.ChatBot.started:
            time.sleep(0.5)

    wish()
    voice_data = None
    while app.ChatBot.started and hub.is_active(Mode.VOICE):
        from_chat = False
        try:
            if app.ChatBot.isUserInput():
                from_chat = True
                voice_data = app.ChatBot.popUserInput()
            else:
                voice_data = record_audio()
        except Exception:
            continue

        if not voice_data or not voice_data.strip():
            continue

        # Optional wake-word gating for microphone input (chat text is exempt).
        if _require_wake_word and not from_chat and 'proton' not in voice_data:
            continue

        # When asleep, only "proton wake up" re-activates
        if not is_awake:
            if (from_chat or 'proton' in voice_data) and any(w in voice_data for w in ['wake', 'up']):
                is_awake = True
                wish()
            continue

        # When awake: process commands (wake-word may be required via config)
        try:
            macro_cmds = _split_macro_commands(_normalize_voice_text(voice_data))
            for i, cmd in enumerate(macro_cmds, start=1):
                if len(macro_cmds) > 1:
                    log.info("Macro step %d/%d: %s", i, len(macro_cmds), cmd)
                respond(cmd)
                if _pending_confirmation["action"]:
                    break
        except SystemExit:
            reply("Exit Successful")
            break
        except Exception as e:
            log.error("Command exception: %s", e, exc_info=True)
            continue

    # Cleanup
    hub.stop(Mode.VOICE)
    log.info("Proton voice assistant stopped")