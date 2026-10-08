import os

from dotenv import load_dotenv

from .errors import PipelineError

load_dotenv()


def _get(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def google_key() -> str:
    return _get("GOOGLE_API_KEY")


STT_MODEL = _get("GEMINI_STT_MODEL", "gemini-3.5-transcribe")
REFINE_MODEL = _get("GEMINI_REFINE_MODEL", "gemini-3.5-flash-lite")
DOC_MODEL = _get("GEMINI_DOC_MODEL", "gemini-3.8-flash")
STT_LANGUAGE = _get("STT_LANGUAGE", "en-US")

# Optional. Left unset by default, so each model uses its own recommended setting.
_t = _get("LLM_TEMPERATURE")
TEMPERATURE = float(_t) if _t else None

CHUNK_SECONDS = 1500         # audio is split into 25-minute pieces (the API takes up to 1 hour)
REFINE_CHUNK_CHARS = 5000    # transcript is refined in pieces of about this size


def check_keys() -> None:
    if not google_key():
        raise PipelineError(
            "config",
            "Missing GOOGLE_API_KEY. Add it to the .env file "
            "(copy .env.example to .env) and restart the app.",
        )
