"""محرّك OpenCode: جلسات، مشاريع، وكلاء، نماذج، بث بالاستقصاء، وموافقات."""
from __future__ import annotations

import time

import config
from bridge.core.errors import EngineError
from bridge.core.models import StreamResult
from bridge.infrastructure.engines.opencode.http_client import OpenCodeClient
from bridge.infrastructure.engines.opencode.parser import text_of, tools_of_pairs


def _session(data, fallback_dir=""):
    return {
        "id": data.get("id"),
        "title": data.get("title") or "(بدون عنوان)",
        "dir": (data.get("location") or {}).get("directory") or fallback_dir,
        "updated": (data.get("time") or {}).get("updated") or 0,
    }


class OpenCodeEngine:
    kind = "opencode"
    supports_projects = True
    supports_agents = True
    supports_permissions = True
    rich_cards = True

    def __init__(self, client=None):
        self.client = client or OpenCodeClient()

    # ---------- عقد AgentEngine ----------

    def list_sessions(self, workdir, limit=20):
        try:
            return [self._to_session(s) for s in self.client.sessions()[:limit]]
        except (RuntimeError, ValueError, KeyError) as exc:
            raise EngineError("تعذّر جلب جلسات OpenCode.", detail=str(exc))

    def create_session(self, workdir, title):
        try:
            return self.client.create(title, workdir)
        except (RuntimeError, ValueError, KeyError) as exc:
            raise EngineError("تعذّر إنشاء جلسة OpenCode.", detail=str(exc))

    def stream(self, prompt, *, session_id, workdir, model, on_delta, on_tool,
               on_permission=None):
        if not session_id:
            raise EngineError("لا جلسة OpenCode مفتوحة.")
        sid = session_id
        timeout = config.OPENCODE_TIMEOUT
        try:
            before = [m for m in self.client.messages(sid) if m.get("type") == "assistant"]
            self.client.prompt(sid, prompt)
        except (RuntimeError, ValueError, KeyError) as exc:
            return StreamResult(text="", session_id=sid, error=str(exc))
        deadline = time.time() + timeout
        seen_tools = set()
        seen_perms = set()
        body = ""
        error = None
        while time.time() < deadline:
            time.sleep(1.3)
            try:
                msgs = self.client.messages(sid)
            except (RuntimeError, ValueError):
                continue
            assistants = [m for m in msgs if m.get("type") == "assistant"]
            fresh = assistants[len(before):]
            if fresh:
                current = fresh[-1]
                new_body = text_of(current)
                if new_body and new_body != body:
                    body = new_body
                    on_delta(body)
                for name, detail in tools_of_pairs(current):
                    key = (current.get("id"), name)
                    if key not in seen_tools:
                        seen_tools.add(key)
                        on_tool(name, detail)
                err = current.get("error")
                if err:
                    error = (err.get("message") if isinstance(err, dict) else str(err)) or "خطأ"
                if (current.get("time") or {}).get("completed"):
                    break
            if on_permission:
                for req in self._permissions(sid):
                    rid = req.get("id")
                    if rid and rid not in seen_perms:
                        seen_perms.add(rid)
                        on_permission(req)
        else:
            error = error or "انتهت المهلة دون رد"
        return StreamResult(text=body, session_id=sid, error=error)

    def interrupt(self, session_id=None):
        if not session_id:
            return False
        try:
            self.client.interrupt(session_id)
            return True
        except Exception:  # noqa: BLE001
            return False

    def is_active(self, session_id):
        if not session_id:
            return False
        try:
            return session_id in self.client.active_sessions()
        except Exception:  # noqa: BLE001
            return False

    def list_models(self, workdir):
        return [m["name"] for m in self.list_model_details()]

    def history(self, session_id, limit=40):
        msgs = self.context(session_id)
        out = []
        for msg in msgs[-limit:]:
            if msg.get("type") == "user":
                out.append({"role": "user", "text": (msg.get("text") or "").strip(),
                            "ts": None})
            elif msg.get("type") == "assistant":
                body = text_of(msg)
                if body:
                    out.append({"role": "assistant", "text": body, "ts": None})
        return out

    # ---------- إضافات OpenCode ----------

    def list_projects(self, limit=15):
        try:
            raw = self.client.projects()
        except (RuntimeError, ValueError, KeyError):
            return []
        out = []
        for p in raw:
            out.append({
                "id": p.get("id"),
                "dir": p.get("canonical") or "",
                "vcs": p.get("vcs") or "",
                "active": (p.get("time") or {}).get("active") or 0,
            })
        out.sort(key=lambda x: x["active"], reverse=True)
        return out[:limit]

    def sessions_in(self, directory, limit=20):
        try:
            return [self._to_session(s, directory)
                    for s in self.client.sessions_in(directory, limit)]
        except (RuntimeError, ValueError, KeyError):
            return []

    def session_info(self, sid):
        return self.client.session_info(sid)

    def context(self, sid):
        return self.client.context(sid)

    def list_agents(self, workdir=None):
        try:
            data = self.client.agents(workdir)
        except (RuntimeError, ValueError, KeyError):
            return []
        out = []
        for a in data:
            if a.get("mode") != "primary" or a.get("hidden"):
                continue
            out.append({"id": a.get("id"), "name": a.get("name") or a.get("id"),
                        "desc": (a.get("description") or "")[:90]})
        return out

    def list_model_details(self, limit=40):
        try:
            raw = self.client.models()
        except (RuntimeError, ValueError, KeyError):
            return []
        out = []
        for m in raw:
            mid = m.get("modelID") or m.get("id")
            if not mid:
                continue
            out.append({"id": mid, "provider": m.get("providerID") or "",
                        "name": m.get("name") or mid})
        return out[:limit]

    def set_model(self, sid, model_id, provider=""):
        self.client.set_model(sid, model_id, provider)
        return True

    def set_agent(self, sid, agent_id):
        self.client.set_agent(sid, agent_id)
        return True

    def permissions(self, sid):
        return self._permissions(sid)

    def reply_permission(self, sid, request_id, decision):
        return self.client.reply_permission(sid, request_id, decision)

    # ---------- داخلي ----------

    def _permissions(self, sid):
        try:
            return self.client.permissions(sid)
        except Exception:  # noqa: BLE001
            return []

    @staticmethod
    def _to_session(data, fallback_dir=""):
        return _session(data, fallback_dir)
