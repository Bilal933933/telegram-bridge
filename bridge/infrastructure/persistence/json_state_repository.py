"""حالة كل محادثة في ملف JSON: حزمة لكل محرّك + المحرّك النشط."""
from __future__ import annotations

import json
import threading

import config

ENGINES = ("qoder", "opencode")

# المفتاح ← الحزمة التي يملكه (وإلا يذهب للمحرّك النشط)
OWNER = {
    "oc_session": "opencode",
    "project": "opencode",
    "agent": "opencode",
    "session_id": "qoder",
    "model": "qoder",
}

DEFAULTS = {
    "qoder": {"workdir": None, "session_id": None, "model": None},
    "opencode": {"workdir": None, "project": None, "oc_session": None, "agent": None},
}


def _blank(active="qoder"):
    return {"active": active,
            "qoder": dict(DEFAULTS["qoder"]),
            "opencode": dict(DEFAULTS["opencode"])}


def _migrate(entry):
    """تحويل الملف القديم المسطّح إلى حزمتين (مرة واحدة)."""
    if "qoder" in entry or "opencode" in entry:
        entry.setdefault("active", "qoder")
        for engine in ENGINES:
            entry.setdefault(engine, dict(DEFAULTS[engine]))
        return entry
    qoder = dict(DEFAULTS["qoder"])
    opencode = dict(DEFAULTS["opencode"])
    qoder.update({"workdir": entry.get("workdir"), "session_id": entry.get("session_id"),
                  "model": entry.get("model")})
    opencode.update({"workdir": entry.get("workdir"), "project": entry.get("project"),
                     "oc_session": entry.get("oc_session")})
    return {"active": entry.get("src") or "qoder", "qoder": qoder, "opencode": opencode}


class JsonStateRepository:
    """تنفيذ StateRepository على ملف JSON واحد بكتابة ذرّية."""

    def __init__(self, path=None):
        self.path = path or config.STATE_FILE
        self._lock = threading.Lock()

    def read(self):
        with self._lock:
            if not self.path.exists():
                return {}
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return {}
        return {str(k): _migrate(v) for k, v in raw.items()}

    def write(self, data):
        with self._lock:
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(self.path)

    def entry(self, chat_id):
        return self.read().get(str(chat_id)) or _blank()

    def get(self, chat_id):
        data = self.entry(chat_id)
        active = data["active"]
        ns = data[active]
        return {
            "src": active,
            "workdir": ns.get("workdir") or config.DEFAULT_DIR,
            "model": data["qoder"].get("model"),
            "session_id": data["qoder"].get("session_id"),
            "oc_session": data["opencode"].get("oc_session"),
            "project": data["opencode"].get("project") or "",
            "agent": data["opencode"].get("agent") or "build",
        }

    def ns(self, chat_id, engine):
        data = self.entry(chat_id)
        out = dict(data.get(engine) or DEFAULTS[engine])
        out["workdir"] = out.get("workdir") or config.DEFAULT_DIR
        return out

    def switch(self, chat_id, engine):
        return self.update(chat_id, src=engine)

    def update(self, chat_id, **changes):
        data = self.read()
        item = _migrate(data.setdefault(str(chat_id), _blank()))

        src = changes.pop("src", None)
        if src in ENGINES:
            item["active"] = src
        engine = changes.pop("engine", None) or item["active"]

        for key, value in changes.items():
            if value is None:
                continue
            target = OWNER.get(key, "active")
            bucket = engine if target == "active" else target
            if bucket not in ENGINES:
                continue
            item.setdefault(bucket, dict(DEFAULTS[bucket]))[key] = value
        self.write(data)
        return self.get(chat_id)

    def summary(self, chat_id):
        data = self.entry(chat_id)
        for engine in ENGINES:
            data[engine] = dict(data.get(engine) or DEFAULTS[engine])
            data[engine]["workdir"] = data[engine].get("workdir") or config.DEFAULT_DIR
        return data
