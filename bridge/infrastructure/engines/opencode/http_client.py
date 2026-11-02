"""نداءات OpenCode عبر CLI المدمج (`opencode api ...`) — لا منطق عرض."""
from __future__ import annotations

import json
import os
import subprocess
import urllib.parse

import config


class OpenCodeClient:
    def __init__(self, binary=None, provider=None, model=None):
        self.binary = binary or config.OPENCODE_BIN
        self.provider = provider or config.OPENCODE_PROVIDER
        self.model = model or config.OPENCODE_MODEL

    def call(self, method, path, body=None, timeout=120):
        cmd = [self.binary, "api", method, path]
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

    # ---------- جلسات ----------

    def sessions(self):
        return self.call("get", "/api/session").get("data", []) or []

    def sessions_in(self, directory, limit=20):
        query = urllib.parse.urlencode({"directory": directory, "limit": str(limit),
                                        "order": "desc"})
        return self.call("get", f"/api/session?{query}").get("data", []) or []

    def create(self, title, directory, model=None, provider=None):
        body = {
            "title": title,
            "location": {"directory": directory},
            "model": {
                "id": model or self.model,
                "providerID": provider or self.provider,
                "variant": "default",
            },
        }
        return self.call("post", "/api/session", body)["data"]["id"]

    def session_info(self, sid):
        return self.call("get", f"/api/session/{sid}").get("data") or {}

    def context(self, sid):
        return self.call("get", f"/api/session/{sid}/context").get("data", []) or []

    def messages(self, sid):
        return self.call("get", f"/api/session/{sid}/message").get("data", []) or []

    def prompt(self, sid, text):
        return self.call("post", f"/api/session/{sid}/prompt", {"text": text})

    def interrupt(self, sid):
        self.call("post", f"/api/session/{sid}/interrupt")

    def active_sessions(self):
        return self.call("get", "/api/session/active").get("data", {}) or {}

    def set_model(self, sid, model_id, provider=""):
        body = {"model": {"id": model_id, "providerID": provider or self.provider,
                          "variant": "default"}}
        self.call("post", f"/api/session/{sid}/model", body)

    def set_agent(self, sid, agent_id):
        self.call("post", f"/api/session/{sid}/agent", {"agent": agent_id})

    # ---------- مشاريع/وكلاء/نماذج ----------

    def projects(self):
        raw = self.call("get", "/api/project")
        if isinstance(raw, dict):
            raw = raw.get("data", [])
        return raw or []

    def agents(self, directory=None):
        path = "/api/agent"
        if directory:
            path += "?" + urllib.parse.urlencode({"location[directory]": directory})
        return self.call("get", path).get("data", []) or []

    def models(self):
        raw = self.call("get", "/api/model", timeout=180)
        if isinstance(raw, dict):
            raw = raw.get("data", [])
        return raw or []

    # ---------- أذونات ----------

    def permissions(self, sid):
        return self.call("get", f"/api/session/{sid}/permission").get("data", []) or []

    def reply_permission(self, sid, request_id, decision):
        return self.call("post", f"/api/session/{sid}/permission/{request_id}/reply",
                         {"decision": decision})
