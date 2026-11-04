"""استخدامات الجلسات والمشاريع فوق محرّكات OpenCode (لا تعرف تيليجرام)."""
from __future__ import annotations

import config
from bridge.shared.logging_setup import get_logger

_log = get_logger("sessions")


def _topic_title(path):
    path = (path or "").rstrip("\\/").replace("\\", "/")
    return path.rsplit("/", 1)[-1] or path or "جلسة"


class SessionService:
    def __init__(self, state, engine_get, topics=None):
        self._state = state
        self._engine = engine_get
        self._topics = topics

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
        self._ensure_topic(chat_id, sid, directory)
        return data

    def create(self, chat_id, directory, title=None):
        sid = self._engine("opencode").create_session(directory, title or "تيليجرام")
        self._state.update(chat_id, src="opencode", oc_session=sid,
                           workdir=directory, project=directory)
        self._ensure_topic(chat_id, sid, directory)
        return sid

    def switch_agent(self, sid, agent_id):
        return self._engine("opencode").set_agent(sid, agent_id)

    def switch_model(self, sid, model_id, provider=""):
        return self._engine("opencode").set_model(sid, model_id, provider)

    def context(self, sid):
        return self._engine("opencode").context(sid)

    def _ensure_topic(self, chat_id, sid, directory):
        """موضوع تيليجرام للجلسة (إن كانت الميزة مفعّلة) — الفشل لا يعطّل الجلسة."""
        if not self._topics:
            return
        try:
            self._topics.ensure(chat_id, sid, _topic_title(directory), directory or "")
        except Exception:  # noqa: BLE001
            _log.exception("ensure topic failed session=%s", sid)


class ProjectService:
    """مشاريع وجلسات المحرّك النشط مهما كان نوعه (القدرات تحدد المتاح)."""

    def __init__(self, state, engine_get):
        self._state = state
        self._engine = engine_get

    def active(self, chat_id):
        return self._state.get(chat_id)["src"]

    def engine(self, chat_id):
        return self._engine(self.active(chat_id))

    def list_projects(self, chat_id, limit=12):
        engine = self.engine(chat_id)
        if not getattr(engine, "supports_projects", False):
            return []
        try:
            return engine.list_projects(limit)
        except Exception:  # noqa: BLE001 — قائمة فارغة أفضل من شاشة خطأ
            return []

    def sessions(self, chat_id, directory, limit=20):
        engine = self.engine(chat_id)
        try:
            return engine.sessions_in(directory, limit)
        except Exception:  # noqa: BLE001
            return []

    def rich_cards(self, chat_id):
        return bool(getattr(self.engine(chat_id), "rich_cards", False))

    def workdir_default(self):
        return config.DEFAULT_DIR
