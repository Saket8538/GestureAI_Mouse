"""
AI Brain — LLM-powered intent understanding for Proton voice assistant.

Supports five providers (set via PROTON_AI_PROVIDER in .env):
  - gemini        — Google Gemini
  - openai        — OpenAI  (GPT-4o-mini, GPT-4o, etc.)
  - azure_openai  — Azure OpenAI Service
  - claude        — Anthropic Claude
  - ollama        — local, free, offline

Falls back gracefully to ``None`` when the LLM is unavailable —
the caller (Proton.py) then uses keyword matching as before.

Usage::

    from ai_brain import AIBrain
    brain = AIBrain()                   # reads .env + config.yaml
    result = brain.interpret("copy this and paste into notepad")
    # result = {"actions": [{"type": "hotkey", "keys": ["ctrl","c"]}, ...], "reply": "..."}
    # or None if LLM unavailable
"""

import json
from config_loader import get, env
from logger import log


class AIBrainTransientError(Exception):
    """Raised when the LLM call fails due to a transient issue (rate-limit, timeout, etc.)."""

# ── System prompt that teaches the LLM what actions are available ─────────────
SYSTEM_PROMPT = """\
You are Proton, an AI assistant embedded in a desktop accessibility application.
Your job is to interpret the user's spoken command and return a JSON object with
two keys:
  "actions" — a list of actions to execute (in order)
  "reply"   — a short spoken response to the user

Available action types (use ONLY these):

1. {"type": "click"}                            — left click at current cursor position
2. {"type": "right_click"}                      — right click
3. {"type": "double_click"}                     — double click
4. {"type": "scroll", "direction": "up"|"down", "amount": 5}
5. {"type": "hotkey", "keys": ["ctrl", "c"]}    — press keyboard shortcut
6. {"type": "press", "key": "enter"}            — press a single key (enter, tab, escape, space, delete, backspace, up, down, left, right, f1-f12)
7. {"type": "type_text", "text": "hello"}       — type text into active window
8. {"type": "open_app", "name": "notepad"}      — open a Windows application
9. {"type": "open_url", "url": "https://..."}   — open URL in browser
10. {"type": "search_google", "query": "..."}   — Google search
11. {"type": "search_youtube", "query": "..."}  — YouTube search
12. {"type": "volume", "action": "up"|"down"|"mute"|"unmute"}
13. {"type": "brightness", "action": "up"|"down"}
14. {"type": "screenshot"}                      — take screenshot
15. {"type": "mode", "target": "eye"|"gesture"|"keyboard", "action": "start"|"stop"|"toggle"}
16. {"type": "stop_all_modes"}                  — stop all input modes
17. {"type": "mode_status"}                     — report active modes
18. {"type": "lock_screen"}
19. {"type": "switch_window"}                   — Alt+Tab
20. {"type": "show_desktop"}                    — Win+D
21. {"type": "minimize"}                        — minimize current window
22. {"type": "maximize"}                        — maximize current window
23. {"type": "close_window"}                    — Alt+F4
24. {"type": "navigate_maps", "destination": "..."}
25. {"type": "weather", "location": "..."}
26. {"type": "wikipedia", "topic": "..."}
27. {"type": "sleep"}                           — put Proton to sleep
28. {"type": "exit"}                            — exit Proton

Rules:
- Return ONLY valid JSON. No markdown, no explanation outside the JSON.
- "actions" must be a list (can be empty for conversational replies).
- "reply" must be a short, friendly sentence to speak back.
- For multi-step tasks, chain actions in order (e.g., copy then open notepad then paste).
- If the command is conversational (greeting, joke, question about yourself), return empty actions and just a reply.
- For "open" commands, prefer open_app for desktop apps and open_url for websites.
- Do NOT invent action types not listed above.
- If you are unsure what the user wants, ask for clarification in "reply" with empty actions.
"""


class AIBrain:
    """LLM-backed intent interpreter with conversation memory."""

    def __init__(self):
        # Provider from .env (primary) or config.yaml (fallback)
        self.provider = env("PROTON_AI_PROVIDER") or get("ai.provider", "none")
        self.provider = self.provider.strip().lower()

        self.timeout = get("ai.timeout", 15)
        self.temperature = get("ai.temperature", 0.3)
        self.memory_turns = get("ai.memory_turns", 10)
        self._history: list[dict] = []    # conversation memory
        self._client = None
        self._available = False

        if self.provider == "none" or not self.provider:
            log.info("AI Brain disabled (provider=none in .env)")
            return

        try:
            self._init_provider()
            self._available = True
            log.info("AI Brain ready — provider=%s", self.provider)
        except Exception as e:
            log.warning("AI Brain init failed (%s): %s — falling back to keyword matching", self.provider, e)
            self._available = False

    # ── Provider key helpers ──────────────────────────────────────────────────
    @staticmethod
    def _env_key(name: str) -> str:
        """Get a key from .env, stripped and safe."""
        return env(name, "").strip()

    # ── Provider init ─────────────────────────────────────────────────────────
    def _init_provider(self):
        if self.provider == "openai":
            api_key = self._env_key("PROTON_OPENAI_KEY")
            if not api_key:
                raise ValueError("PROTON_OPENAI_KEY not set in .env")
            import openai
            self._client = openai.OpenAI(api_key=api_key, timeout=self.timeout)
            self._model = env("PROTON_OPENAI_MODEL") or get("ai.openai_model", "gpt-4o-mini")

        elif self.provider == "azure_openai":
            api_key = self._env_key("PROTON_AZURE_OPENAI_KEY")
            endpoint = self._env_key("PROTON_AZURE_OPENAI_ENDPOINT")
            deployment = self._env_key("PROTON_AZURE_OPENAI_DEPLOYMENT")
            api_ver = env("PROTON_AZURE_OPENAI_API_VERSION", "2024-06-01").strip()
            if not api_key or not endpoint or not deployment:
                raise ValueError(
                    "Set PROTON_AZURE_OPENAI_KEY, PROTON_AZURE_OPENAI_ENDPOINT, "
                    "and PROTON_AZURE_OPENAI_DEPLOYMENT in .env"
                )
            import openai
            self._client = openai.AzureOpenAI(
                api_key=api_key,
                azure_endpoint=endpoint,
                api_version=api_ver,
                timeout=self.timeout,
            )
            self._model = deployment  # Azure uses deployment name as model

        elif self.provider == "gemini":
            api_key = self._env_key("PROTON_GEMINI_KEY")
            if not api_key:
                raise ValueError("PROTON_GEMINI_KEY not set in .env")
            from google import genai as ggenai
            self._client = ggenai.Client(api_key=api_key)
            self._model = env("PROTON_GEMINI_MODEL") or get("ai.gemini_model", "gemini-2.0-flash")

        elif self.provider == "claude":
            api_key = self._env_key("PROTON_CLAUDE_KEY")
            if not api_key:
                raise ValueError("PROTON_CLAUDE_KEY not set in .env")
            import anthropic
            self._client = anthropic.Anthropic(api_key=api_key)
            self._model = env("PROTON_CLAUDE_MODEL") or get("ai.claude_model", "claude-sonnet-4-20250514")

        elif self.provider == "ollama":
            import httpx
            base = env("PROTON_OLLAMA_URL") or get("ai.ollama_url", "http://localhost:11434")
            base = base.strip().rstrip("/")
            # Quick health check
            resp = httpx.get(f"{base}/api/tags", timeout=5)
            resp.raise_for_status()
            self._model = env("PROTON_OLLAMA_MODEL") or get("ai.ollama_model", "llama3.2")
            self._ollama_url = base

        else:
            raise ValueError(f"Unknown AI provider: '{self.provider}'. "
                             f"Valid: gemini, openai, azure_openai, claude, ollama, none")

    @property
    def available(self) -> bool:
        return self._available

    def interpret(self, user_text: str) -> dict | None:
        """Send user text to LLM and get structured actions + reply.

        Returns dict {"actions": [...], "reply": "..."} or None on failure.
        """
        if not self._available:
            return None

        try:
            raw = self._call_llm(user_text)
            if not raw:
                return None

            # Parse JSON from LLM response
            result = self._parse_response(raw)
            if result:
                # Update conversation history
                self._history.append({"role": "user", "content": user_text})
                self._history.append({"role": "assistant", "content": raw})
                # Trim to memory limit
                max_msgs = self.memory_turns * 2
                if len(self._history) > max_msgs:
                    self._history = self._history[-max_msgs:]
            return result

        except Exception as e:
            err_str = str(e).lower()
            is_transient = any(kw in err_str for kw in [
                '429', 'rate', 'resource_exhausted', 'quota', 'too many requests',
                'timeout', 'timed out', 'unavailable', 'overloaded',
            ])
            log.error("AI Brain interpret failed: %s", e)
            if is_transient:
                raise AIBrainTransientError(str(e)) from e
            return None

    def _call_llm(self, user_text: str) -> str | None:
        """Call the configured LLM provider and return raw text response."""
        if self.provider == "openai" or self.provider == "azure_openai":
            return self._call_openai(user_text)
        elif self.provider == "gemini":
            return self._call_gemini(user_text)
        elif self.provider == "claude":
            return self._call_claude(user_text)
        elif self.provider == "ollama":
            return self._call_ollama(user_text)
        return None

    def _call_openai(self, user_text: str) -> str | None:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(self._history)
        messages.append({"role": "user", "content": user_text})

        resp = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=1024,
            response_format={"type": "json_object"},
        )
        return resp.choices[0].message.content

    def _call_gemini(self, user_text: str) -> str | None:
        from google.genai import types
        # Build conversation contents
        contents = []
        for msg in self._history:
            role = "user" if msg["role"] == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part(text=msg["content"])]))
        contents.append(types.Content(role="user", parts=[types.Part(text=user_text)]))

        resp = self._client.models.generate_content(
            model=self._model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=self.temperature,
                max_output_tokens=1024,
            ),
        )
        return resp.text

    def _call_claude(self, user_text: str) -> str | None:
        messages = []
        messages.extend(self._history)
        messages.append({"role": "user", "content": user_text})

        resp = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=messages,
            temperature=self.temperature,
        )
        # Claude returns content blocks; extract text
        return resp.content[0].text if resp.content else None

    def _call_ollama(self, user_text: str) -> str | None:
        import httpx
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(self._history)
        messages.append({"role": "user", "content": user_text})

        resp = httpx.post(
            f"{self._ollama_url}/api/chat",
            json={
                "model": self._model,
                "messages": messages,
                "stream": False,
                "format": "json",
                "options": {"temperature": self.temperature},
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json().get("message", {}).get("content", "")

    def _parse_response(self, raw: str) -> dict | None:
        """Extract valid JSON from LLM response text."""
        text = raw.strip()

        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first and last fence lines
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON object in the text
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    data = json.loads(text[start:end])
                except json.JSONDecodeError:
                    log.warning("AI Brain: could not parse LLM response as JSON")
                    return None
            else:
                log.warning("AI Brain: no JSON found in LLM response")
                return None

        # Validate structure
        if not isinstance(data, dict):
            return None
        if "actions" not in data:
            data["actions"] = []
        if "reply" not in data:
            data["reply"] = ""
        if not isinstance(data["actions"], list):
            data["actions"] = []

        return data

    def clear_memory(self):
        """Reset conversation history."""
        self._history.clear()
        log.info("AI Brain conversation memory cleared")
