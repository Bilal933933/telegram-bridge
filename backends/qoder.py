"""محرك Qoder CLI: قائمة الجلسات/النماذج + تشغيل بوضع stream-json + قراءة المحادثات."""
import json
import os
import re
import subprocess
import time
from pathlib import Path

import config

SESS_RE = re.compile(r"^\s*(\d+)\.\s+(.*?)\s+\(([^)]*)\)\s+\[([0-9a-fA-F-]{8,})\]\s*$")
CURRENT = {"proc": None}
HISTORY_DIR = config.BASE / "qoder_history"
PROJECTS_DIR = Path.home() / ".qoder" / "projects"
MAX_TEXT = 8000


def history_file(session_id):
    return HISTORY_DIR / f"{session_id}.jsonl"


def log_turn(session_id, user_text, assistant_text="", error=None):
    """يسجّل الدور محليًا (Qoder لا يحفظ نص المحادثة على القرص)."""
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



def stop():
    proc = CURRENT.get("proc")
    if proc and proc.poll() is None:
        proc.kill()
        return True
    return False


def _run(args, timeout=90):
    flags = 0x08000000 if os.name == "nt" else 0
    try:
        p = subprocess.run([config.QODER] + args, capture_output=True, timeout=timeout,
                           creationflags=flags)
    except subprocess.TimeoutExpired:
        return 1, "", "timeout"
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def list_sessions(workdir):
    _, out, err = _run(["--list-sessions", "-w", workdir])
    items = []
    for line in (out + "\n" + err).splitlines():
        m = SESS_RE.match(line)
        if m:
            items.append({"index": int(m.group(1)), "title": m.group(2),
                          "when": m.group(3), "id": m.group(4)})
    return items


def list_models(workdir):
    _, out, _ = _run(["--list-models", "-w", workdir], timeout=45)
    return [ln.strip() for ln in out.splitlines() if ln.strip() and not ln.strip().upper().startswith("MODEL")]


def _result_text(stdout):
    raw = stdout.strip()
    if not raw:
        return "", None, None
    try:
        data = json.loads(raw)
    except ValueError:
        return raw, None, None
    if isinstance(data, dict):
        sid = data.get("session_id")
        err = data.get("result") if data.get("is_error") else None
        for key in ("result", "response", "text", "content", "message", "output", "answer"):
            val = data.get(key)
            if isinstance(val, str) and val.strip():
                return val, sid, err
    return raw, None, None


def stream(prompt, session_id, workdir, model, on_delta, on_tool):
    cmd = [config.QODER, "-p", prompt, "-o", "stream-json", "-w", workdir,
           "--permission-mode", config.QODER_MODE]
    if model:
        cmd += ["-m", model]
    if session_id:
        cmd += ["--resume", session_id]  # --session-id تُنشئ جلسة، والاستئناف بـ --resume
    flags = 0x08000000 if os.name == "nt" else 0
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            cwd=workdir if os.path.isdir(workdir) else None,
                            text=True, encoding="utf-8", errors="replace", bufsize=1,
                            creationflags=flags)
    CURRENT["proc"] = proc
    text = ""
    sid = session_id
    error = None
    noise = []
    try:
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except ValueError:
                noise.append(line)
                continue
            etype = ev.get("type")
            if etype == "assistant":
                for block in (ev.get("message") or {}).get("content") or []:
                    btype = block.get("type")
                    if btype == "text" and block.get("text"):
                        text = block["text"] if not text else text + block["text"]
                        on_delta(text)
                    elif btype == "tool_use":
                        on_tool(block.get("name") or "tool",
                                json.dumps(block.get("input") or {}, ensure_ascii=False))
            elif etype == "result":
                sid = ev.get("session_id") or sid
                if ev.get("is_error"):
                    error = str(ev.get("result"))[:500]
                elif not text and ev.get("result"):
                    text = ev["result"]
                    on_delta(text)
        proc.wait()
    finally:
        if proc.poll() is None:
            proc.kill()
        CURRENT["proc"] = None
    if not text and not error:
        detail = " · ".join(noise[-2:]).strip() if noise else ""
        error = detail or f"Qoder لم يُرجع ردًا (رمز الخروج {proc.returncode})"
    return text, sid, error


def stop(proc=None):
    return False
