"""محرك OpenCode: جلسات، بتاريخها، بث بالاستقصاء، موافقات، ومشاريع."""
import json
import os
import subprocess
import time
import urllib.parse

import config


def _api(method, path, body=None, timeout=120):
    cmd = [config.OPENCODE_BIN, "api", method, path]
    if body is not None:
        cmd += ["--data", json.dumps(body, ensure_ascii=False)]
    flags = 0x08000000 if os.name == "nt" else 0
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout, creationflags=flags)
    raw = (r.stdout or "").strip()
    if r.returncode != 0:
        raise RuntimeError(raw[:400] or (r.stderr or "").strip()[:400] or "فشل الطلب")
    if not raw:
        return {}  # 204 No Content (مثل تبديل النموذج/الوكيل)
    try:
        return json.loads(raw)
    except ValueError:
        return {"raw": raw}


def list_sessions(limit=20):
    data = _api("get", "/api/session").get("data", [])
    out = []
    for s in data[:limit]:
        out.append({
            "id": s.get("id"),
            "title": s.get("title") or "(بدون عنوان)",
            "dir": (s.get("location") or {}).get("directory") or "",
            "updated": (s.get("time") or {}).get("updated") or 0,
        })
    return out


def create(title, directory, model=None, provider=None):
    body = {
        "title": title,
        "location": {"directory": directory},
        "model": {
            "id": model or config.OPENCODE_MODEL,
            "providerID": provider or config.OPENCODE_PROVIDER,
            "variant": "default",
        },
    }
    return _api("post", "/api/session", body)["data"]["id"]


def messages(sid):
    return _api("get", f"/api/session/{sid}/message").get("data", [])


def projects(limit=15):
    """المشاريع المعروفة لدى OpenCode (أحدث نشاطًا أولًا)."""
    raw = _api("get", "/api/project")
    if isinstance(raw, dict):
        raw = raw.get("data", [])
    out = []
    for p in raw or []:
        out.append({
            "id": p.get("id"),
            "dir": p.get("canonical") or "",
            "vcs": p.get("vcs") or "",
            "active": (p.get("time") or {}).get("active") or 0,
        })
    out.sort(key=lambda x: x["active"], reverse=True)
    return out[:limit]


def sessions_in(directory, limit=20):
    """جلسات مشروع واحد فقط."""
    query = urllib.parse.urlencode({"directory": directory, "limit": str(limit),
                                    "order": "desc"})
    data = _api("get", f"/api/session?{query}").get("data", []) or []
    out = []
    for s in data:
        out.append({
            "id": s.get("id"),
            "title": s.get("title") or "(بدون عنوان)",
            "dir": (s.get("location") or {}).get("directory") or directory,
            "updated": (s.get("time") or {}).get("updated") or 0,
        })
    return out


def session_info(sid):
    """تفاصيل الجلسة: الموديل، الوكيل، الرموز، التكلفة، الحالة."""
    return _api("get", f"/api/session/{sid}").get("data") or {}


def context(sid):
    """كل رسائل الجلسة كما يراها المحرك (تشمل الرموز لكل رسالة)."""
    return _api("get", f"/api/session/{sid}/context").get("data", []) or []


def agents(directory=None):
    """الوكلاء الأساسيون المتاحون (مثل Tab في البرنامج)."""
    path = "/api/agent"
    if directory:
        path += "?" + urllib.parse.urlencode({"location[directory]": directory})
    data = _api("get", path).get("data", []) or []
    out = []
    for a in data:
        if a.get("mode") != "primary" or a.get("hidden"):
            continue
        out.append({"id": a.get("id"), "name": a.get("name") or a.get("id"),
                    "desc": (a.get("description") or "")[:90]})
    return out


def models(limit=40):
    """نماذج OpenCode المتاحة عبر مزوّديها."""
    raw = _api("get", "/api/model", timeout=180)
    if isinstance(raw, dict):
        raw = raw.get("data", [])
    out = []
    for m in raw or []:
        mid = m.get("modelID") or m.get("id")
        if not mid:
            continue
        out.append({"id": mid, "provider": m.get("providerID") or "",
                    "name": m.get("name") or mid})
    return out[:limit]


def set_model(sid, model_id, provider=""):
    body = {"model": {"id": model_id, "providerID": provider or config.OPENCODE_PROVIDER,
                      "variant": "default"}}
    _api("post", f"/api/session/{sid}/model", body)
    return True


def set_agent(sid, agent_id):
    _api("post", f"/api/session/{sid}/agent", {"agent": agent_id})
    return True


def diff(sid):
    try:
        return _api("get", f"/api/session/{sid}/diff").get("data") or []
    except Exception:  # noqa: BLE001
        return []


def is_active(sid):
    try:
        return sid in _api("get", "/api/session/active").get("data", {})
    except Exception:  # noqa: BLE001
        return False


def interrupt(sid):
    try:
        _api("post", f"/api/session/{sid}/interrupt")
        return True
    except Exception:  # noqa: BLE001
        return False


def permissions(sid):
    try:
        return _api("get", f"/api/session/{sid}/permission").get("data", [])
    except Exception:  # noqa: BLE001
        return []


def reply_permission(sid, request_id, decision):
    return _api("post", f"/api/session/{sid}/permission/{request_id}/reply",
                {"decision": decision})


def _text_of(msg):
    parts = []
    for part in msg.get("content") or []:
        if part.get("type") == "text" and part.get("text"):
            parts.append(part["text"])
    return "\n".join(parts).strip()


def _tools_of(msg):
    out = []
    for part in msg.get("content") or []:
        if part.get("type") in ("text", "reasoning"):
            continue
        name = part.get("tool") or part.get("name") or part.get("type")
        out.append((name, ""))
    return out


def text_of(msg):
    return _text_of(msg)


def tools_of(msg):
    return [name for name, _ in _tools_of(msg)]


def stream(sid, text, on_delta, on_tool, on_permission, timeout=None, poll=1.3):
    timeout = timeout or config.OPENCODE_TIMEOUT
    before = [m for m in messages(sid) if m.get("type") == "assistant"]
    _api("post", f"/api/session/{sid}/prompt", {"text": text})
    deadline = time.time() + timeout
    seen_tools = set()
    seen_perms = set()
    body = ""
    error = None
    while time.time() < deadline:
        time.sleep(poll)
        msgs = messages(sid)
        assistants = [m for m in msgs if m.get("type") == "assistant"]
        fresh = assistants[len(before):]
        if fresh:
            current = fresh[-1]
            new_body = _text_of(current)
            if new_body and new_body != body:
                body = new_body
                on_delta(body)
            for name, detail in _tools_of(current):
                key = (current.get("id"), name)
                if key not in seen_tools:
                    seen_tools.add(key)
                    on_tool(name, detail)
            err = current.get("error")
            if err:
                error = (err.get("message") if isinstance(err, dict) else str(err)) or "خطأ"
            if (current.get("time") or {}).get("completed"):
                break
        for req in permissions(sid):
            rid = req.get("id")
            if rid and rid not in seen_perms:
                seen_perms.add(rid)
                on_permission(req)
    else:
        error = error or "انتهت المهلة دون رد"
    return body, error


def history(sid, limit=30):
    msgs = messages(sid)
    lines = []
    for msg in msgs[-limit:]:
        if msg.get("type") == "user":
            lines.append(f"👤 {msg.get('text') or ''}".strip())
        elif msg.get("type") == "assistant":
            body = _text_of(msg)
            if body:
                lines.append(f"🤖 {body}".strip())
            for name, _ in _tools_of(msg):
                lines.append(f"⚙ {name}")
    return "\n\n".join(lines)
