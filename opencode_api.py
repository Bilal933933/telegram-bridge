#!/usr/bin/env python3
"""مغلّف رقيق على OpenCode HTTP API عبر CLI المدمج (opencode api ...)."""
import json
import os
import subprocess
import time

EXE = os.environ.get(
    "OPENCODE_BIN",
    r"C:\Users\blals\AppData\Roaming\npm\node_modules\@opencode\cli\bin\opencode.exe",
)
PROVIDER = os.environ.get("OPENCODE_PROVIDER", "opencode")
MODEL = os.environ.get("OPENCODE_MODEL", "deepseek-v4.1-flash-free")


def _api(method, path, body=None, timeout=120):
    cmd = [EXE, "api", method, path]
    if body is not None:
        cmd += ["--data", json.dumps(body, ensure_ascii=False)]
    flags = 0x08000000 if os.name == "nt" else 0
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout, creationflags=flags)
    if r.returncode != 0:
        raise RuntimeError((r.stdout or "").strip()[:400] or (r.stderr or "").strip()[:400])
    return json.loads(r.stdout)


def sessions(limit=15):
    data = _api("get", "/api/session").get("data", [])
    out = []
    for s in data[:limit]:
        loc = s.get("location") or {}
        out.append({
            "id": s.get("id"),
            "title": s.get("title") or "(بدون عنوان)",
            "dir": loc.get("directory") or "",
            "updated": (s.get("time") or {}).get("updated") or 0,
        })
    return out


def create(title, directory, model=None, provider=None):
    body = {
        "title": title,
        "location": {"directory": directory},
        "model": {"id": model or MODEL, "providerID": provider or PROVIDER, "variant": "default"},
    }
    return _api("post", "/api/session", body)["data"]["id"]


def _messages(sid):
    return _api("get", f"/api/session/{sid}/message").get("data", [])


def _text_of(msg):
    parts = []
    for part in msg.get("content") or []:
        if part.get("type") == "text" and part.get("text"):
            parts.append(part["text"])
    return "\n".join(parts).strip()


def prompt(sid, text, timeout=420, poll=2.5):
    before = [m for m in _messages(sid) if m.get("type") == "assistant"]
    _api("post", f"/api/session/{sid}/prompt", {"text": text})
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        time.sleep(poll)
        msgs = _messages(sid)
        assistants = [m for m in msgs if m.get("type") == "assistant"]
        fresh = assistants[len(before):]
        if not fresh:
            continue
        msg = fresh[-1]
        if not (msg.get("time") or {}).get("completed"):
            continue
        body = _text_of(msg)
        err = msg.get("error")
        if err:
            last_error = (err.get("message") if isinstance(err, dict) else str(err)) or "خطأ غير معروف"
        return body, last_error
    return "", "انتهت المهلة دون رد"


def interrupt(sid):
    try:
        _api("post", f"/api/session/{sid}/interrupt")
        return True
    except Exception:  # noqa: BLE001
        return False


def is_active(sid):
    try:
        active = _api("get", "/api/session/active").get("data", {})
        return sid in active
    except Exception:  # noqa: BLE001
        return False
