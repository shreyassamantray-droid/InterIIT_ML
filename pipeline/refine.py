"""Stage 2: domain-aware transcript refinement (Gemini)."""
import json
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path

from . import config, llm

PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"
MAX_LENGTH_CHANGE = 0.15   # refined chunk may differ in word count by at most 15%
MIN_SIMILARITY = 0.85      # word-level similarity to the raw chunk


@dataclass
class RefineResult:
    text: str
    glossary: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _prompt(name: str) -> str:
    return (PROMPT_DIR / name).read_text(encoding="utf-8")


def extract_glossary(raw: str) -> list[str]:
    try:
        out = llm.gemini_text(_prompt("glossary.txt"), raw[:60000], config.REFINE_MODEL, json_mode=True)
        terms = json.loads(out)
        return [str(t).strip() for t in terms if str(t).strip()][:40] if isinstance(terms, list) else []
    except Exception:  # noqa: BLE001 - glossary is optional
        return []


def split_chunks(text: str, max_chars: int) -> list[str]:
    """Group paragraphs into chunks of at most ~max_chars (a paragraph is never split)."""
    paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks, cur, size = [], [], 0
    for p in paragraphs:
        if cur and size + len(p) > max_chars:
            chunks.append("\n\n".join(cur))
            cur, size = [], 0
        cur.append(p)
        size += len(p)
    if cur:
        chunks.append("\n\n".join(cur))
    return chunks


def _clean_output(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\n|\n```$", "", text).strip()
    lines = text.split("\n")
    # drop a chatty preamble like "Here is the corrected transcript:"
    if lines and re.match(r"^(here('s| is)|sure|certainly|corrected)\b.*:\s*$", lines[0].strip(), re.I):
        text = "\n".join(lines[1:]).strip()
    return text


def drift_ok(raw: str, refined: str) -> bool:
    a, b = raw.split(), refined.split()
    if not a:
        return True
    if not b or abs(len(b) - len(a)) / len(a) > MAX_LENGTH_CHANGE:
        return False
    return SequenceMatcher(None, a, b, autojunk=False).ratio() >= MIN_SIMILARITY


def refine(raw: str, user_hint: str = "", progress=None) -> RefineResult:
    system = _prompt("refine.txt")

    if progress:
        progress("refine", "update", "Identifying domain terms")
    glossary = extract_glossary(raw)
    if user_hint.strip():
        glossary = [t.strip() for t in re.split(r"[,\n]", user_hint) if t.strip()] + glossary

    chunks = split_chunks(raw, config.REFINE_CHUNK_CHARS)
    out_chunks, warnings = [], []
    gloss_line = ("Known or likely terms: " + ", ".join(glossary) + "\n\n") if glossary else ""

    for i, chunk in enumerate(chunks, 1):
        if progress:
            progress("refine", "update", f"Refining part {i} of {len(chunks)}")
        try:
            refined = _clean_output(
                llm.gemini_text(system, f"{gloss_line}Transcript to correct:\n\n{chunk}", config.REFINE_MODEL)
            )
        except Exception as e:  # noqa: BLE001
            warnings.append(f"Part {i}: refinement failed ({e}); the raw text was kept for this part.")
            out_chunks.append(chunk)
            continue
        if not drift_ok(chunk, refined):
            warnings.append(f"Part {i}: the refined text differed too much from the raw text, "
                            "so the raw text was kept for this part.")
            out_chunks.append(chunk)
        else:
            out_chunks.append(refined)

    return RefineResult(text="\n\n".join(out_chunks), glossary=glossary, warnings=warnings)
