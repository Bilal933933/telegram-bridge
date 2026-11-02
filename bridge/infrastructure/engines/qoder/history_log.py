"""حفظ وقراءة محادثات Qoder.

Qoder لا يحفظ نص المحادثة دائمًا، لذا:
1) نقرأ ملف المحادثة الكامل من ~/.qoder/projects إن وُجد،
2) وإلا نستخدم سجلًا محليًا نسجّله عند كل دور.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import config

HISTORY_DIR = config.BASE / "qoder_history"
PROJECTS_DIR = Path.home() / ".qoder" / "projects"
MAX_TEXT = 8000


def history_file(session_id):
    return HISTORY_DIR / f"{session_id}.jsonl"


def log_turn(session_id, user_text, assistant_text="", error=None):
    """يسجّل الدور محليًا."""
    if not session_id:
        return
    try:
        HISTORY_DIR.mkdir(exist_ok=True)
        with history_file(session_id).open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"role": "user", "text": user_text[:MAX_TEXT],
                                 "ts": time.time()}, ensure_ascii=False) + "\n")
            body = (assistant_text or (f"⚠️ {error}" if error else "")).strip()
            if body:
                fh.write(json.dumps({"role": "assistant", "text": body[:MAX_TEXT],
                                     "ts": time.time()}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def read_history(session_id, limit=40):
    path = history_file(session_id)
    if not path.exists():
        return []
    out = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    except OSError:
        return []
    return out[-limit:] if limit else out


def transcript_file(session_id):
    """ملف محادثة Qoder الكامل: ~/.qoder/projects/<مشروع>/<جلسة>.jsonl"""
    if not session_id:
        return None
    try:
        hits = sorted(PROJECTS_DIR.glob(f"*/{session_id}.jsonl"),
                      key=lambda p: p.stat().st_mtime)
    except OSError:
        return None
    return hits[-1] if hits else None


def _text_of(message):
    content = (message or {}).get("content")
    if isinstance(content, str):
        return content.strip()
    parts = []
    for block in content or []:
        if isinstance(block, dict) and block.get("type") == "text":
            text = (block.get("text") or "").strip()
            if text:
                parts.append(text)
    return "\n\n".join(parts)


def read_transcript(session_id, limit=40):
    """يقرأ محادثة الجلسة من ملف Qoder (يشمل ما جرى داخل البرنامج والبوت)."""
    path = transcript_file(session_id)
    if not path:
        return []
    out = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except ValueError:
            continue
        if item.get("isSidechain"):
            continue
        kind = item.get("type")
        if kind not in ("user", "assistant"):
            continue
        text = _text_of(item.get("message"))
        if text:
            out.append({"role": kind, "text": text[:MAX_TEXT],
                        "ts": item.get("timestamp")})
    return out[-limit:] if limit else out


def read_messages(session_id, limit=40):
    """محادثة الجلسة: ملف Qoder أولًا، ثم السجل المحلي كبديل."""
    if not session_id:
        return []
    entries = read_transcript(session_id, limit)
    if entries:
        return entries
    return read_history(session_id, limit)
