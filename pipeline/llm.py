"""Thin wrappers around the Google Gemini client, with retries."""
import time

from . import config

_gemini = None


def gemini_client():
    global _gemini
    if _gemini is None:
        from google import genai
        _gemini = genai.Client(api_key=config.google_key())
    return _gemini


def with_retries(fn, attempts: int = 3, base_delay: float = 2.0):
    last = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            last = e
            if i < attempts - 1:
                time.sleep(base_delay * (2 ** i))
    raise last


def _generate(system: str, user: str, model: str, **extra) -> str:
    from google.genai import types

    cfg = dict(system_instruction=system, **extra)
    if config.TEMPERATURE is not None:
        cfg["temperature"] = config.TEMPERATURE

    resp = gemini_client().models.generate_content(
        model=model, contents=user, config=types.GenerateContentConfig(**cfg)
    )
    cand = resp.candidates[0] if resp.candidates else None
    if cand is None:
        raise RuntimeError("Gemini returned no candidates (possibly blocked).")
    if "MAX_TOKENS" in str(getattr(cand, "finish_reason", "")):
        raise RuntimeError("Gemini output was truncated.")
    text = resp.text
    if not text or not text.strip():
        raise RuntimeError("Gemini returned an empty response.")
    return text


def gemini_text(system: str, user: str, model: str, json_mode: bool = False) -> str:
    extra = {"response_mime_type": "application/json"} if json_mode else {}
    return with_retries(lambda: _generate(system, user, model, **extra))


def gemini_structured(system: str, user: str, model: str, schema, parse):
    """Ask for JSON that matches `schema`; `parse` turns the text into an object.
    Parsing is inside the retry, so invalid JSON gets another try."""
    def call():
        text = _generate(system, user, model,
                         response_mime_type="application/json", response_schema=schema)
        return parse(text)
    return with_retries(call)


def gemini_transcribe(path: str, model: str, language: str = "", vocabulary=None) -> str:
    client = gemini_client()
    if not hasattr(client, "interactions"):
        raise RuntimeError("The google-genai package is too old for transcription. "
                           "Run: pip install -U google-genai")

    def call():
        f = client.files.upload(file=str(path))
        try:
            for _ in range(30):  # wait until the upload is ready
                state = getattr(getattr(f, "state", None), "name", None)
                if state != "PROCESSING":
                    break
                time.sleep(1)
                f = client.files.get(name=f.name)

            tc = {}
            if language:
                tc["language_codes"] = [language]
            if vocabulary:
                tc["custom_vocabulary"] = list(vocabulary)[:100]
            kwargs = dict(
                model=model,
                input=[{"type": "audio", "uri": f.uri, "mime_type": f.mime_type or "audio/mp3"}],
            )
            if tc:
                kwargs["generation_config"] = {"transcription_config": tc}
            return client.interactions.create(**kwargs).output_text or ""
        finally:
            try:
                client.files.delete(name=f.name)
            except Exception:  # noqa: BLE001
                pass

    return with_retries(call)
