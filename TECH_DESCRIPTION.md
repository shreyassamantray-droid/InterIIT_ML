# Technical Description: AI Meeting Assistant

## What it does

You upload a meeting recording. The app gives back a raw transcript, a cleaned transcript, and a meeting record with a summary, minutes, decisions and action items. It all runs in one go from a web page.

## Models

All three models are from Google Gemini and use one API key.

| Step | Model | Job |
|---|---|---|
| Speech-to-text | `gemini-3.5-transcribe` | Turns the audio into text |
| Language model 1 (refiner) | `gemini-3.5-flash-lite` | Fixes words the speech model got wrong, like tech terms and acronyms |
| Language model 2 (writer) | `gemini-3.8-flash` | Writes the summary, minutes, decisions and action items |

The two language models are separate steps with separate instructions and different models. Model names are set in the `.env` file.

## How data moves

```
Audio file
  -> check the file
  -> split into 25-minute pieces (16 kHz mono MP3)
  -> Speech-to-text  -> RAW TRANSCRIPT
  -> Refiner         -> REFINED TRANSCRIPT
  -> Writer          -> MEETING RECORD (JSON)
  -> Markdown + JSON files, shown in the app
```

1. **Check the file.** The app rejects wrong file types, empty files, broken files and silent files, and shows a clear message.
2. **Speech-to-text.** Each audio piece is uploaded to the speech model. If the user typed in domain terms, they are sent as a custom word list. The pieces are joined and split into paragraphs. This is the raw transcript. It is kept as is.
3. **Refiner.** First, the model lists the technical terms it sees in the raw transcript. Then the transcript goes through the refiner in chunks, along with that term list (and any terms the user typed in). The refiner is told to fix only clear hearing mistakes, and to never change names, numbers, "not", or promises. The result is the refined transcript.
4. **Writer.** The refined transcript (not the raw one) goes to the writer model. It must answer in a fixed format (a schema), so the output is always valid JSON.
5. **Output.** The same JSON is used to make the Markdown and the JSON files, so both always say the same thing.

## Rules that keep the output honest

- **No made-up owners or dates.** If the recording does not say who or when, the field is set to `Unspecified`.
- **Proposals are not decisions.** Only clearly agreed items are listed as decisions or tasks. Ideas, open questions and unassigned suggestions go in a separate "open items" list.
- **Proof for each item.** Every decision, task and open item has a short quote from the transcript. The app checks that the quote really appears in the transcript, and flags it if not.
- **Refiner guard.** After each refined chunk, the app compares it to the raw chunk. If the length or wording changed too much, it keeps the raw chunk and shows a warning.
- **Fallbacks.** If a refiner call fails, that chunk stays raw. Failed calls are retried up to 3 times.
- **No hardcoded results.** Everything comes from the models at run time.

## Outputs

`raw_transcript.txt`, `refined_transcript.txt`, `meeting_minutes.md`, `key_decisions.md`, `action_items.md`, `meeting_record.md` (readable), `meeting_record.json` (machine-readable), plus a zip of all of them.

## Limits

- English audio only.
- No speaker names or labels.
- Audio is cut at fixed 25-minute marks, so a word at a cut point may be lost on very long recordings.
- Quality depends on audio quality.
