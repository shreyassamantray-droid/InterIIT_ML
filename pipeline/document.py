"""Stage 3: minutes, decisions and action items (Gemini, structured output)."""
import re
from difflib import SequenceMatcher
from pathlib import Path

from . import config, llm
from .errors import PipelineError
from .models import MeetingRecord

PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"
UNSPECIFIED = "Unspecified"
_EMPTY_VALUES = {"", "n/a", "na", "none", "null", "tbd", "unknown", "unspecified", "not specified", "not stated"}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", s.lower())).strip()


def evidence_verified(evidence: str, transcript_norm: str) -> bool:
    ev = _norm(evidence)
    if not ev:
        return False
    if ev in transcript_norm:
        return True
    m = SequenceMatcher(None, ev, transcript_norm, autojunk=False).find_longest_match(
        0, len(ev), 0, len(transcript_norm))
    return m.size / len(ev) >= 0.7


def _unspecified(value: str | None) -> str:
    if value is None or value.strip().lower() in _EMPTY_VALUES:
        return UNSPECIFIED
    return value.strip()


def generate_record(refined: str) -> tuple[dict, list[str]]:
    """Return (record dict, warnings)."""
    system = (PROMPT_DIR / "document.txt").read_text(encoding="utf-8")
    try:
        obj = llm.gemini_structured(
            system, f"Refined transcript:\n\n{refined}", config.DOC_MODEL,
            MeetingRecord, MeetingRecord.model_validate_json,
        )
    except Exception as e:  # noqa: BLE001
        raise PipelineError("document", f"The minutes-generation service failed: {e}") from e

    record = obj.model_dump()
    t_norm = _norm(refined)
    warnings = []

    for a in record["action_items"]:
        a["owner"] = _unspecified(a["owner"])
        a["deadline"] = _unspecified(a["deadline"])
    for key in ("decisions", "action_items", "open_items"):
        for item in record[key]:
            item["evidence_verified"] = evidence_verified(item["evidence"], t_norm)
            if not item["evidence_verified"]:
                label = item.get("decision") or item.get("task") or item.get("item")
                warnings.append(f"Could not match the supporting quote for '{label}' to the transcript; "
                                "please check it manually.")
    return record, warnings
