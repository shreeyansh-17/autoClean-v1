"""Configuration loading for AutoClean."""
import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Try loading from .env in development (won't exist or shouldn't be bundled in production)
load_dotenv()


def get_user_data_dir() -> Path:
    """Returns the writable user-data directory for AutoClean on Windows/Linux/macOS."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        base = Path(local_app_data)
    else:
        base = Path.home() / "AppData" / "Local"
    app_dir = base / "AutoClean"
    try:
        app_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        # Fallback to home directory if LOCALAPPDATA is inaccessible
        app_dir = Path.home() / ".autoclean"
        app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


USER_DATA_DIR = get_user_data_dir()
SETTINGS_FILE = USER_DATA_DIR / "settings.json"


def load_user_settings() -> dict:
    """Reads persistent user settings from user data directory."""
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


_user_settings = load_user_settings()

GROQ_API_KEY = _user_settings.get("groq_api_key") or os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = _user_settings.get("groq_model") or os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
MAX_SAMPLE_VALUES = int(_user_settings.get("max_sample_values", os.getenv("MAX_SAMPLE_VALUES", "5")))
LLM_TEMPERATURE = float(_user_settings.get("llm_temperature", os.getenv("LLM_TEMPERATURE", "0.1")))
LLM_MAX_RETRIES = int(_user_settings.get("llm_max_retries", os.getenv("LLM_MAX_RETRIES", "3")))

# Privacy: set SEND_SAMPLE_VALUES=false to stop real cell values from being included in the profile
SEND_SAMPLE_VALUES = str(
    _user_settings.get("send_sample_values", os.getenv("SEND_SAMPLE_VALUES", "true"))
).strip().lower() not in ("0", "false", "no")

# Profiles larger than this many characters are split into column batches
MAX_PROMPT_CHARS = int(_user_settings.get("max_prompt_chars", os.getenv("MAX_PROMPT_CHARS", "20000")))

# If the LLM is unavailable/fails, apply a conservative rule-based plan instead of cleaning nothing.
FALLBACK_ON_LLM_FAILURE = str(
    _user_settings.get("fallback_on_llm_failure", os.getenv("FALLBACK_ON_LLM_FAILURE", "true"))
).strip().lower() not in ("0", "false", "no")


def update_setting(key: str, value) -> None:
    """Updates a runtime config variable and persists to settings.json."""
    global GROQ_API_KEY, GROQ_MODEL, MAX_SAMPLE_VALUES, LLM_TEMPERATURE, LLM_MAX_RETRIES
    global SEND_SAMPLE_VALUES, MAX_PROMPT_CHARS, FALLBACK_ON_LLM_FAILURE

    settings = load_user_settings()
    settings[key] = value
    try:
        SETTINGS_FILE.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    except Exception:
        pass

    if key == "groq_api_key":
        GROQ_API_KEY = str(value)
        os.environ["GROQ_API_KEY"] = str(value)
    elif key == "groq_model":
        GROQ_MODEL = str(value)
        os.environ["GROQ_MODEL"] = str(value)
    elif key == "max_sample_values":
        MAX_SAMPLE_VALUES = int(value)
    elif key == "llm_temperature":
        LLM_TEMPERATURE = float(value)
    elif key == "llm_max_retries":
        LLM_MAX_RETRIES = int(value)
    elif key == "send_sample_values":
        SEND_SAMPLE_VALUES = str(value).strip().lower() not in ("0", "false", "no")
    elif key == "max_prompt_chars":
        MAX_PROMPT_CHARS = int(value)
    elif key == "fallback_on_llm_failure":
        FALLBACK_ON_LLM_FAILURE = str(value).strip().lower() not in ("0", "false", "no")
