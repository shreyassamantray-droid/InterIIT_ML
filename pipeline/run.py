"""Orchestration: validate -> transcribe -> refine -> document."""
from dataclasses import dataclass, field

from . import config, document, refine, render, stt, validate
from .errors import PipelineError


@dataclass
class PipelineResult:
    raw: str
    refined: str
    record: dict
    duration: float
    glossary: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    files: dict[str, bytes] = field(default_factory=dict)


def run_pipeline(path: str, original_name: str, hint: str = "", progress=None) -> PipelineResult:
    """progress(stage, status, detail): status is 'start', 'update' or 'done'."""
    def emit(stage, status, detail=""):
        if progress:
            progress(stage, status, detail)

    config.check_keys()

    emit("validate", "start", "Checking the file")
    duration = validate.validate_audio(path, original_name)
    emit("validate", "done", f"Audio OK ({duration / 60:.1f} min)")

    emit("transcribe", "start", "Transcribing speech")
    raw = stt.transcribe(path, hint, progress)
    emit("transcribe", "done", f"{len(raw.split())} words transcribed")

    emit("refine", "start", "Refining domain terms")
    rr = refine.refine(raw, hint, progress)
    emit("refine", "done", "Transcript refined")

    emit("document", "start", "Generating minutes, decisions and action items")
    record, doc_warnings = document.generate_record(rr.text)
    emit("document", "done", "Meeting record ready")

    files = render.build_files(raw, rr.text, record)
    return PipelineResult(raw=raw, refined=rr.text, record=record, duration=duration,
                          glossary=rr.glossary, warnings=rr.warnings + doc_warnings, files=files)
