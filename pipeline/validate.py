"""Input validation: file type, emptiness, decodability, silence."""
import re
import shutil
import subprocess
from pathlib import Path

from .errors import PipelineError

ALLOWED_EXT = {".mp3", ".wav", ".m4a", ".mp4", ".aac", ".ogg", ".flac", ".webm", ".opus"}
MIN_SECONDS = 1.0
SILENCE_DB = -50.0  # if the loudest sample is below this, treat the file as silent


def _need_ffmpeg() -> None:
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise PipelineError(
            "validate",
            "ffmpeg/ffprobe is not installed on this machine. Install ffmpeg and restart the app.",
        )


def validate_audio(path: str, original_name: str) -> float:
    """Return the duration in seconds, or raise PipelineError with a clear message."""
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_EXT:
        raise PipelineError(
            "validate",
            f"Unsupported file type '{ext or original_name}'. "
            f"Please upload an audio file ({', '.join(sorted(ALLOWED_EXT))}).",
        )

    p = Path(path)
    if not p.exists() or p.stat().st_size == 0:
        raise PipelineError("validate", "The uploaded file is empty.")

    _need_ffmpeg()

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(p)],
        capture_output=True, text=True,
    )
    try:
        duration = float(probe.stdout.strip())
    except ValueError:
        duration = -1.0
    if probe.returncode != 0 or duration < 0:
        raise PipelineError(
            "validate",
            "The file could not be read as audio. It may be corrupted or not a real audio file.",
        )
    if duration < MIN_SECONDS:
        raise PipelineError("validate", "The audio is too short to contain a meeting.")

    vol = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(p), "-vn", "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    m = re.search(r"max_volume:\s*(-?[\d.]+|-inf)\s*dB", vol.stderr)
    if m is None:
        raise PipelineError("validate", "The file does not appear to contain an audio track.")
    max_db = float("-inf") if m.group(1) == "-inf" else float(m.group(1))
    if max_db <= SILENCE_DB:
        raise PipelineError("validate", "The recording appears to be silent, so there is nothing to transcribe.")

    return duration
