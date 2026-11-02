"""استطلاع getUpdates: كل تحديث في خيط محمي، وأي خطأ يُسجّل ولا يوقف الحلقة."""
from __future__ import annotations

import functools
import threading
import time
import urllib.error

from bridge.shared.logging_setup import get_logger

_log = get_logger("poller")
_ERROR_SLEEP = 5


def _chat_id(callback_query):
    return (callback_query.get("message") or {}).get("chat", {}).get("id")


class TelegramPoller:
    def __init__(self, ctx, commands, callbacks):
        self._ctx = ctx
        self._commands = commands
        self._callbacks = callbacks

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
                self._route(update)

    # ---------- التوجيه ----------

    def _route(self, update):
        if "callback_query" in update:
            query = update["callback_query"]
            self._spawn(_chat_id(query), self._on_callback, query)
            return
        message = update.get("message") or {}
        chat_id = (message.get("chat") or {}).get("id")
        text = message.get("text") or ""
        if chat_id != self._ctx.owner or not text:
            return
        self._spawn(chat_id, self._on_message, chat_id, text)

    def _on_message(self, chat_id, text):
        self._commands.dispatch(self._ctx, chat_id, text)

    def _on_callback(self, query):
        chat_id = _chat_id(query)
        self._ctx.tg.answer(query.get("id"))
        if chat_id != self._ctx.owner:
            return
        self._callbacks.dispatch(self._ctx, chat_id, query.get("data") or "")

    def _spawn(self, chat_id, handler, *args):
        threading.Thread(
            target=self._ctx.boundary.run,
            args=(chat_id, functools.partial(handler, *args)),
            daemon=True,
        ).start()
