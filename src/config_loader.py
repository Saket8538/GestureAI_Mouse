"""
Centralised configuration loader.

Loads environment variables from ``.env`` (API keys, provider choice) first,
then reads ``config.yaml`` for tuning constants.  Any module can do::

    from config_loader import cfg, get, env
    alpha = cfg["eye"]["ema_alpha"]
    key   = env("PROTON_GEMINI_KEY")       # from .env
"""

import os

# ── dotenv — load .env into os.environ early ──────────────────────────────────
def _find_file(name: str) -> str:
    """Walk up from src/ to find *name* in the project root."""
    here = os.path.dirname(os.path.abspath(__file__))
    for _ in range(5):
        candidate = os.path.join(here, name)
        if os.path.isfile(candidate):
            return candidate
        here = os.path.dirname(here)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', name)


# Load .env so every os.environ.get() picks up the user's keys
_dotenv_path = _find_file(".env")
if os.path.isfile(_dotenv_path):
    try:
        from dotenv import load_dotenv
        load_dotenv(_dotenv_path, override=False)   # existing env vars win
    except ImportError:
        # Manual fallback: parse KEY=VALUE lines
        with open(_dotenv_path, "r", encoding="utf-8") as _f:
            for _line in _f:
                _line = _line.strip()
                if not _line or _line.startswith("#"):
                    continue
                if "=" in _line:
                    _k, _, _v = _line.partition("=")
                    _k, _v = _k.strip(), _v.strip().strip('"\'')
                    if _k and _k not in os.environ:        # don't overwrite
                        os.environ[_k] = _v

# ── YAML config ───────────────────────────────────────────────────────────────
import yaml   # noqa: E402  (must come after dotenv load)

def _load() -> dict:
    path = _find_file("config.yaml")
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


cfg: dict = _load()


def get(dotpath: str, default=None):
    """Retrieve a nested value using dot-separated keys.

    >>> get("ai.timeout", 15)
    15
    """
    keys = dotpath.split(".")
    node = cfg
    for k in keys:
        if isinstance(node, dict) and k in node:
            node = node[k]
        else:
            return default
    return node if node is not None else default


def env(name: str, default: str = "") -> str:
    """Read an environment variable (loaded from .env at startup).

    >>> env("PROTON_GEMINI_KEY")
    'AIza...'
    """
    return os.environ.get(name, default)


def reload():
    """Re-read config.yaml (call if user edits it at runtime)."""
    global cfg
    cfg.clear()
    cfg.update(_load())
