"""Stage 1: speech-to-text (Gemini Transcribe)."""
import re
import subprocess
import tempfile
from pathlib import Path

from . import config, llm
from .errors import PipelineError


def _split_audio(src: str, workdir: Path) -> list[Path]:
    """Convert to 16 kHz mono MP3 and cut into fixed-length chunks."""
    pattern = workdir / "chunk_%03d.mp3"
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", src, "-vn", "-ar", "16000", "-ac", "1",
        "-c:a", "libmp3lame", "-b:a", "32k",
        "-f", "segment", "-segment_format", "mp3",
        "-segment_time", str(config.CHUNK_SECONDS), "-reset_timestamps", "1",
        str(pattern),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    chunks = sorted(workdir.glob("chunk_*.mp3"))
    if r.returncode != 0 or not chunks:
        raise PipelineError("transcribe", "Could not convert the audio for transcription: " + r.stderr[-300:])
    return chunks


def paragraphize(text: str, sentences_per_paragraph: int = 4) -> str:
    """Break a wall of text into readable paragraphs."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    paras = [" ".join(sentences[i:i + sentences_per_paragraph])
             for i in range(0, len(sentences), sentences_per_paragraph)]
    return "\n\n".join(p for p in paras if p)


def transcribe(src: str, hint: str = "", progress=None) -> str:
    vocabulary = [t.strip() for t in re.split(r"[,\n]", hint) if t.strip()]
    texts = []
    with tempfile.TemporaryDirectory() as td:
        chunks = _split_audio(src, Path(td))
        for i, chunk in enumerate(chunks, 1):
            if progress:
                progress("transcribe", "update", f"Transcribing part {i} of {len(chunks)}")
            try:
                texts.append(llm.gemini_transcribe(str(chunk), config.STT_MODEL,
                                                   config.STT_LANGUAGE, vocabulary))
            except Exception as e:  # noqa: BLE001
                raise PipelineError("transcribe", f"The transcription service failed: {e}") from e

    raw = " ".join(t.strip() for t in texts if t and t.strip())
    if len(raw.split()) < 3:
        raise PipelineError("transcribe", "No speech was detected in the recording.")
    return paragraphize(raw)
