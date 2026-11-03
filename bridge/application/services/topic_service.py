"""موضوعات تيليجرام: موضوع مستقل لكل جلسة OpenCode، وروابط فتحها."""
from __future__ import annotations

import config
from bridge.shared.logging_setup import get_logger

_log = get_logger("topics")


class TopicService:
    def __init__(self, tg, store, group_id=None):
        self._tg = tg
        self._store = store
        self._fallback_group = group_id if group_id is not None else config.GROUP_CHAT_ID

    @property
    def group(self):
        """معرّف المجموعة: من التخزين (‎/setup‎) أو من .env، أو None."""
        return self._store.group() or self._fallback_group or None

    def bind_group(self, chat_id):
        self._store.bind_group(chat_id)

    def ensure(self, chat_id, session_id, title="", directory=""):
        """يعيد موضوع الجلسة، وينشئه مرة واحدة إن لزم. None إن كانت الميزة معطّلة."""
        existing = self._store.thread_of(session_id)
        if existing:
            return existing
        group = self.group
        if not group:
            return None
        name = f"📁 {title or 'جلسة'} · {session_id[-6:]}"
        try:
            thread_id = self._tg.create_topic(group, name)
        except Exception as exc:  # noqa: BLE001 — صلاحية ناقصة أو Topics غير مفعّلة
            _log.warning("create topic failed group=%s session=%s: %s",
                         group, session_id, exc)
            return None
        if not thread_id:
            return None
        self._store.bind(thread_id, chat_id, session_id, directory)
        return thread_id

    def resolve(self, thread_id):
        return self._store.resolve(thread_id)

    def thread_for(self, session_id):
        return self._store.thread_of(session_id)

    def link(self, session_id):
        """رابط فتح موضوع الجلسة داخل تيليجرام، أو '' إن لم يوجد موضوع."""
        thread_id = self._store.thread_of(session_id)
        group = self.group
        if not thread_id or not group:
            return ""
        internal = str(group)
        if internal.startswith("-100"):
            internal = internal[4:]
        return f"https://t.me/c/{internal}/{thread_id}"
