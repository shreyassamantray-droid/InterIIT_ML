# Meeting Assistant

Upload a recorded English meeting and get a raw transcript, a domain-refined transcript, structured minutes, key decisions and action items, all from one run.

## Pipeline

All three models are Google Gemini, so you only need one API key.

| Stage | Model | Role |
|---|---|---|
| 1. Speech-to-text | `gemini-3.5-transcribe` | Audio to raw transcript |
| 2. Refinement (LLM-A) | `gemini-3.5-flash-lite` | Fixes recognition errors in technical terms and acronyms without changing meaning |
| 3. Documentation (LLM-B) | `gemini-3.6-flash` | Refined transcript to summary, minutes, decisions, action items (structured JSON output) |

Models are set in `.env` and can be changed there.

Safeguards:
- **Refinement drift guard:** each refined chunk is compared with its raw chunk. If it changes too much (length or wording), the raw chunk is kept and a warning is shown.
- **Proposals are not decisions:** the documenter puts only clearly agreed items under decisions. Unsettled proposals, questions and unassigned suggestions go under "open items".
- **Owners and deadlines** are only filled in when stated. Otherwise they show as `Unspecified` in both the Markdown and JSON outputs.
- **Evidence check:** every decision, task and open item carries a verbatim quote, which is checked against the transcript. Unmatched quotes are flagged for review.

## Setup

Requires Python 3.10+ and **ffmpeg** (includes ffprobe).

```bash
# ffmpeg: Ubuntu/Debian: sudo apt install ffmpeg | macOS: brew install ffmpeg | Windows: winget install ffmpeg
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -U -r requirements.txt   # needs a recent google-genai
cp .env.example .env             # then put your GOOGLE_API_KEY in .env
streamlit run app.py
```

## Using the app

1. Upload an audio file (mp3, wav, m4a, mp4, aac, ogg, flac, webm, opus).
2. Optionally enter domain terms or acronyms as hints.
3. Click **Process recording** and watch the stage status.
4. Inspect the tabs (raw, refined, diff, minutes, decisions, action items, full record) and download any output, or everything as a zip.

## Outputs

`raw_transcript.txt`, `refined_transcript.txt`, `meeting_minutes.md`, `key_decisions.md`, `action_items.md`, `meeting_record.md` (human-readable) and `meeting_record.json` (machine-readable). The two record formats are generated from the same data, so they always match.

## Error handling

Clear messages are shown for: unsupported file types, empty files, unreadable/corrupt audio, silent audio, recordings with no detectable speech, a missing API key, missing ffmpeg, and failures from the Gemini service (with retries).

## Project layout

```
app.py                 Streamlit interface
pipeline/
  config.py            Reads .env (keys, model names)
  validate.py          File checks
  stt.py               Stage 1: transcription (chunked)
  refine.py            Stage 2: refinement + drift guard
  document.py          Stage 3: structured record + evidence check
  models.py            Pydantic schema for the record
  render.py            Markdown / JSON / diff / zip
  run.py               Orchestration
prompts/               All model instructions
samples/               Sample recording and generated outputs
```

## Notes

- Audio is converted to 16 kHz mono MP3 and split into 25-minute pieces for transcription.
- Speaker labels (diarization) are not produced.
