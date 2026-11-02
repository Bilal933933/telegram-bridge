"""استخدامات الجلسات والمشاريع فوق محرّكات OpenCode (لا تعرف تيليجرام)."""
from __future__ import annotations

import config


class SessionService:
    def __init__(self, state, engine_get):
        self._state = state
        self._engine = engine_get

    def info(self, sid):
        return self._engine("opencode").session_info(sid)

    def busy(self, sid):
        return self._engine("opencode").is_active(sid)

    def open(self, chat_id, sid, directory=None):
        """فتح جلسة قائمة بنفس معرّفها الحقيقي (resume لا نسخة)."""
        data = self.info(sid)
        directory = directory or (data.get("location") or {}).get("directory")
        self._state.update(chat_id, src="opencode", oc_session=sid,
                           workdir=directory or self._state.get(chat_id)["workdir"],
                           project=directory or "")
        return data

    def create(self, chat_id, directory, title=None):
        sid = self._engine("opencode").create_session(directory, title or "تيليجرام")
        self._state.update(chat_id, src="opencode", oc_session=sid,
                           workdir=directory, project=directory)
        return sid

    def switch_agent(self, sid, agent_id):
        return self._engine("opencode").set_agent(sid, agent_id)

    def switch_model(self, sid, model_id, provider=""):
        return self._engine("opencode").set_model(sid, model_id, provider)

    def context(self, sid):
        return self._engine("opencode").context(sid)


class ProjectService:
    def __init__(self, engine_get):
        self._engine = engine_get

    def list_projects(self, limit=12):
        return self._engine("opencode").list_projects(limit)

    def sessions(self, directory, limit=20):
        return self._engine("opencode").sessions_in(directory, limit)

    def workdir_default(self):
        return config.DEFAULT_DIR
