"""Configuration loading for AutoClean."""
import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
MAX_SAMPLE_VALUES = int(os.getenv("MAX_SAMPLE_VALUES", "5"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "3"))

# Privacy: set SEND_SAMPLE_VALUES=false to stop real cell values (up to MAX_SAMPLE_VALUES per column)
# from being included in the profile sent to the LLM. Only stats and issue tags are sent then.
SEND_SAMPLE_VALUES = os.getenv("SEND_SAMPLE_VALUES", "true").strip().lower() not in ("0", "false", "no")
# Profiles larger than this many characters are split into column batches (several smaller LLM calls).
MAX_PROMPT_CHARS = int(os.getenv("MAX_PROMPT_CHARS", "20000"))
# If the LLM is unavailable/fails, apply a conservative rule-based plan instead of cleaning nothing.
FALLBACK_ON_LLM_FAILURE = os.getenv("FALLBACK_ON_LLM_FAILURE", "true").strip().lower() not in ("0", "false", "no")
