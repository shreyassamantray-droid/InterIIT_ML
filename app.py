import os
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from pipeline import config, render
from pipeline.errors import PipelineError
from pipeline.run import run_pipeline

st.set_page_config(page_title="Meeting Assistant", page_icon="📝", layout="wide")
st.title("AI Meeting Assistant")
st.caption(
    f"Speech-to-text: `{config.STT_MODEL}` → Transcript refinement: `{config.REFINE_MODEL}` "
    f"→ Minutes & tasks: `{config.DOC_MODEL}` (all Google Gemini)"
)

STAGES = {
    "validate": "1. Checking file",
    "transcribe": "2. Transcribing audio",
    "refine": "3. Refining transcript",
    "document": "4. Generating meeting record",
}

uploaded = st.file_uploader(
    "Upload a meeting recording (English)",
    type=[e.lstrip(".") for e in sorted(__import__("pipeline.validate", fromlist=["x"]).ALLOWED_EXT)],
)
hint = st.text_input(
    "Optional: domain terms or acronyms that may appear (comma-separated)",
    placeholder="e.g. Kubernetes, OKR, Q3 roadmap",
)
start = st.button("Process recording", type="primary", disabled=uploaded is None)

if start and uploaded is not None:
    st.session_state.pop("result", None)
    st.session_state.pop("error", None)
    suffix = Path(uploaded.name).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded.getbuffer())
        tmp_path = tmp.name

    status = st.status("Starting…", expanded=True)

    def progress(stage, state, detail=""):
        label = STAGES.get(stage, stage)
        if state == "start":
            status.update(label=f"{label}…")
            status.write(f"⏳ {label}")
        elif state == "update":
            status.update(label=f"{label}: {detail}")
        elif state == "done":
            status.write(f"✅ {label}: {detail}")

    try:
        st.session_state["result"] = run_pipeline(tmp_path, uploaded.name, hint, progress)
        status.update(label="Done", state="complete", expanded=False)
    except PipelineError as e:
        st.session_state["error"] = f"**{STAGES.get(e.stage, e.stage)} failed.** {e.message}"
        status.update(label="Failed", state="error", expanded=True)
    except Exception as e:  # noqa: BLE001
        st.session_state["error"] = f"**Unexpected error.** {e}"
        status.update(label="Failed", state="error", expanded=True)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

if "error" in st.session_state:
    st.error(st.session_state["error"])

res = st.session_state.get("result")
if res:
    for w in res.warnings:
        st.warning(w)

    tabs = st.tabs(["Raw transcript", "Refined transcript", "Compare", "Minutes",
                    "Key decisions", "Action items", "Full record"])
    rec, files = res.record, res.files

    def dl(label, name, mime="text/plain"):
        st.download_button(label, files[name], file_name=name, mime=mime, key=f"dl_{name}")

    with tabs[0]:
        st.text_area("Raw transcript", res.raw, height=420, disabled=True, label_visibility="collapsed")
        dl("Download raw transcript", "raw_transcript.txt")
    with tabs[1]:
        st.text_area("Refined transcript", res.refined, height=420, disabled=True, label_visibility="collapsed")
        if res.glossary:
            st.caption("Domain terms used as hints: " + ", ".join(res.glossary))
        dl("Download refined transcript", "refined_transcript.txt")
    with tabs[2]:
        st.caption("Red = removed from raw, green = added by refinement.")
        st.markdown(render.diff_html(res.raw, res.refined), unsafe_allow_html=True)
    with tabs[3]:
        st.markdown(render.minutes_md(rec))
        dl("Download minutes", "meeting_minutes.md", "text/markdown")
    with tabs[4]:
        st.markdown(render.decisions_md(rec))
        dl("Download key decisions", "key_decisions.md", "text/markdown")
    with tabs[5]:
        if rec["action_items"]:
            st.dataframe(
                pd.DataFrame([{"Task": a["task"], "Owner": a["owner"], "Deadline": a["deadline"]}
                              for a in rec["action_items"]]),
                use_container_width=True, hide_index=True,
            )
        else:
            st.markdown(render.actions_md(rec))
        dl("Download action items", "action_items.md", "text/markdown")
        oi = render.open_items_md(rec)
        if oi:
            st.subheader("Open items (not decided or assigned)")
            st.markdown(oi)
    with tabs[6]:
        st.markdown(render.record_md(rec))
        c1, c2, c3 = st.columns(3)
        with c1:
            dl("Download record (Markdown)", "meeting_record.md", "text/markdown")
        with c2:
            dl("Download record (JSON)", "meeting_record.json", "application/json")
        with c3:
            st.download_button("Download everything (.zip)", render.zip_files(files),
                               file_name="meeting_outputs.zip", mime="application/zip", key="dl_zip")
