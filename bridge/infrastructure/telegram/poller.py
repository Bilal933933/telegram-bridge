"""استطلاع getUpdates: كل تحديث في خيط محمي، وأي خطأ يُسجّل ولا يوقف الحلقة."""
from __future__ import annotations

import functools
import threading
import time
import urllib.error

from bridge.shared.logging_setup import get_logger

_log = get_logger("poller")
_ERROR_SLEEP = 5
_GROUP_TYPES = ("group", "supergroup")


def _sender(message):
    return (message.get("from") or {}).get("id")


class TelegramPoller:
    def __init__(self, ctx):
        self._ctx = ctx

    def run(self):
        offset = 0
        while True:
            try:
                res = self._ctx.tg.call(
                    "getUpdates", offset=offset, timeout=30,
                    allowed_updates='["message","callback_query"]',
                )
            except urllib.error.HTTPError as exc:
                _log.warning("getUpdates HTTP %s", exc.code)
                time.sleep(_ERROR_SLEEP)
                continue
            except Exception:  # noqa: BLE001
                _log.exception("loop error")
                time.sleep(_ERROR_SLEEP)
                continue
            for update in res.get("result", []):
                offset = update["update_id"] + 1
                try:
                    self._route(update)
                except Exception:  # noqa: BLE001 — تحديث واحد لا يوقف الحلقة
                    _log.exception("update error id=%s", update.get("update_id"))

    # ---------- التوجيه ----------

    def _route(self, update):
        if "callback_query" in update:
            self._route_callback(update["callback_query"])
            return
        message = update.get("message") or {}
        chat = message.get("chat") or {}
        text = message.get("text") or ""
        if not text or _sender(message) != self._ctx.owner:
            return
        if chat.get("id") == self._ctx.owner:
            self._spawn(chat.get("id"), None, self._on_message, chat.get("id"), text)
            return
        if chat.get("type") in _GROUP_TYPES:
            self._route_group(chat.get("id"), message.get("message_thread_id"), text)

    def _route_group(self, group_id, thread_id, text):
        """مواضيع الجلسات: نعيد ربط الحالة بالجلسة ثم نوجّه كالمعتاد."""
        if not thread_id:
            if text.split()[:1] == ["/setup"]:
                self._spawn(group_id, None, self._on_setup, group_id)
            return
        binding = self._ctx.topics.resolve(thread_id)
        if not binding:
            return
        owner_chat = self._bind_topic(binding)
        self._spawn(owner_chat, thread_id, self._on_message, owner_chat, text)

    def _route_callback(self, query):
        message = query.get("message") or {}
        chat = message.get("chat") or {}
        thread_id = message.get("message_thread_id")
        try:  # إغلاق «جارٍ التنفيذ» ليس حرجًا: فشله لا يوقف التوجيه
            self._ctx.tg.answer(query.get("id"))
        except Exception:  # noqa: BLE001
            _log.warning("answer failed")
        if _sender(query) != self._ctx.owner:
            return
        if chat.get("id") == self._ctx.owner:
            self._spawn(chat.get("id"), None, self._on_callback, query, chat.get("id"))
            return
        if chat.get("type") in _GROUP_TYPES and thread_id:
            binding = self._ctx.topics.resolve(thread_id)
            if not binding:
                return
            owner_chat = self._bind_topic(binding)
            self._spawn(owner_chat, thread_id, self._on_callback, query, owner_chat)

    def _bind_topic(self, binding):
        """يجعل جلسة الموضوع هي النشطة قبل تنفيذ الأمر أو الرسالة."""
        owner_chat = binding["chat"]
        directory = binding.get("dir") or None
        changes = {"src": "opencode", "oc_session": binding["session"]}
        if directory:
            changes["workdir"] = directory
            changes["project"] = directory
        self._ctx.state.update(owner_chat, **changes)
        return owner_chat

    # ---------- المعالجات ----------

    def _on_message(self, chat_id, text):
        self._ctx.command_router.dispatch(self._ctx, chat_id, text)

    def _on_callback(self, query, chat_id):
        self._ctx.callback_router.dispatch(self._ctx, chat_id, query.get("data") or "")

    def _on_setup(self, group_id):
        self._ctx.topics.bind_group(group_id)
        self._ctx.messenger.send(
            group_id,
            "✅ تم ربط هذه المجموعة. كل جلسة جديدة ستُفتح في موضوع مستقل هنا.",
        )

    # ---------- الخيوط ----------

    def _spawn(self, chat_id, thread_id, handler, *args):
        action = functools.partial(handler, *args)
        threading.Thread(
            target=self._guarded,
            args=(chat_id, thread_id, action),
            daemon=True,
        ).start()

    def _guarded(self, chat_id, thread_id, action):
        self._ctx.delivery.begin(thread_id)
        try:
            self._ctx.boundary.run(chat_id, action)
        finally:
            self._ctx.delivery.clear()
