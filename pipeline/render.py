"""Human-readable and machine-readable outputs, all generated from one record."""
import html
import io
import json
import zipfile
from difflib import SequenceMatcher


def _flag(item: dict) -> str:
    return "" if item.get("evidence_verified", True) else " ⚠ _quote not verified_"


def minutes_md(rec: dict) -> str:
    out = ["## Summary", "", rec["summary"], "", "## Minutes", ""]
    if not rec["minutes"]:
        out.append("_No discussion topics recorded._")
    for sec in rec["minutes"]:
        out += [f"### {sec['topic']}", ""] + [f"- {p}" for p in sec["points"]] + [""]
    return "\n".join(out).strip() + "\n"


def decisions_md(rec: dict) -> str:
    if not rec["decisions"]:
        return "_No decisions were made in this meeting._\n"
    return "\n".join(f"{i}. {d['decision']}{_flag(d)}\n   > {d['evidence']}"
                     for i, d in enumerate(rec["decisions"], 1)) + "\n"


def actions_md(rec: dict) -> str:
    if not rec["action_items"]:
        return "_No action items were assigned in this meeting._\n"
    return "\n".join(
        f"{i}. **{a['task']}**{_flag(a)}\n   - Owner: {a['owner']}\n   - Deadline: {a['deadline']}\n   > {a['evidence']}"
        for i, a in enumerate(rec["action_items"], 1)) + "\n"


def open_items_md(rec: dict) -> str:
    if not rec["open_items"]:
        return ""
    labels = {"proposal": "Proposal (not agreed)", "question": "Open question", "tentative_task": "Tentative task (not assigned)"}
    return "\n".join(f"- **{labels[o['kind']]}:** {o['item']}{_flag(o)}" for o in rec["open_items"]) + "\n"


def record_md(rec: dict) -> str:
    parts = ["# Meeting Record", "", minutes_md(rec), "## Key Decisions", "", decisions_md(rec),
             "## Action Items", "", actions_md(rec)]
    oi = open_items_md(rec)
    if oi:
        parts += ["## Open Items (not decided)", "", oi]
    return "\n".join(parts)


def record_json(rec: dict) -> str:
    return json.dumps(rec, indent=2, ensure_ascii=False)


def diff_html(raw: str, refined: str) -> str:
    """Word-level diff: removed words struck through in red, added words in green."""
    a, b = raw.split(" "), refined.split(" ")
    parts = []
    for op, i1, i2, j1, j2 in SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op == "equal":
            parts.append(html.escape(" ".join(a[i1:i2])))
        else:
            if i2 > i1:
                parts.append('<del style="background:#fdd;color:#900">' + html.escape(" ".join(a[i1:i2])) + "</del>")
            if j2 > j1:
                parts.append('<ins style="background:#dfd;color:#060;text-decoration:none">' + html.escape(" ".join(b[j1:j2])) + "</ins>")
    return '<div style="line-height:1.7;white-space:pre-wrap">' + " ".join(parts) + "</div>"


def build_files(raw: str, refined: str, rec: dict) -> dict[str, bytes]:
    files = {
        "raw_transcript.txt": raw,
        "refined_transcript.txt": refined,
        "meeting_minutes.md": "# Meeting Minutes\n\n" + minutes_md(rec),
        "key_decisions.md": "# Key Decisions\n\n" + decisions_md(rec),
        "action_items.md": "# Action Items\n\n" + actions_md(rec),
        "meeting_record.md": record_md(rec),
        "meeting_record.json": record_json(rec),
    }
    return {k: v.encode("utf-8") for k, v in files.items()}


def zip_files(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)
    return buf.getvalue()
