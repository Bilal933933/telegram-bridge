"""تنفيذ رسالة على المحرّك النشط وبثّ الرد — مسار واحد للجميع."""
from __future__ import annotations

import functools
import threading

from bridge.core.models import StreamResult
from bridge.infrastructure.telegram.streamer import Streamer
from bridge.infrastructure.telegram.typing_indicator import start_typing
from bridge.shared.logging_setup import get_logger

_log = get_logger("prompt_runner")


class PromptRunner:
    def __init__(self, ctx):
        self.ctx = ctx

    def submit(self, chat_id, text):
        """يحجز المحادثة ثم ينفّذ الرسالة في خيط محمي بالـ ErrorBoundary."""
        if not self.ctx.busy.try_acquire(chat_id):
            self.ctx.messenger.send(chat_id, "⏳ فيه مهمة شغالة. أرسل /stop.")
            return
        st = self.ctx.state.get(chat_id)
        target = self._run_opencode if st["src"] == "opencode" else self._run_qoder
        threading.Thread(
            target=self.ctx.boundary.run,
            args=(chat_id, functools.partial(target, chat_id, text)),
            daemon=True,
        ).start()

    # ---------- المحرّكان ----------

    def _run_qoder(self, chat_id, text):
        try:
            st = self.ctx.state.get(chat_id)
            engine = self.ctx.engines.get("qoder")
            sid = st["session_id"]
            result, streamer = self._stream(chat_id, engine, sid, text)
            if result.session_id and result.session_id != sid:
                self.ctx.state.update(chat_id, session_id=result.session_id)
            engine.log_turn(result.session_id or sid, text, result.text, result.error)
            self._finish(streamer, result)
        finally:
            self.ctx.busy.release(chat_id)

    def _run_opencode(self, chat_id, text):
        try:
            st = self.ctx.state.get(chat_id)
            engine = self.ctx.engines.get("opencode")
            sid = st["oc_session"]
            if not sid:
                try:
                    sid = engine.create_session(st["workdir"], "تيليجرام")
                except Exception as exc:  # noqa: BLE001
                    _log.exception("opencode create session failed chat=%s", chat_id)
                    self.ctx.messenger.send(chat_id, f"⚠️ تعذر إنشاء جلسة:\n{exc}")
                    return
                self.ctx.state.update(chat_id, oc_session=sid)
            if engine.is_active(sid):
                self.ctx.messenger.send(
                    chat_id,
                    "⏳ **هذه الجلسة مشغولة** بردّ جارٍ.\nافتح جلسة أخرى أو أنشئ جديدة:",
                    self.ctx.keyboards.kb([
                        [{"text": "🆕 جلسة جديدة", "callback_data": "new"}],
                        [{"text": "💬 جلسات المشروع", "callback_data": "sessions"}],
                    ]),
                )
                return
            result, streamer = self._stream(chat_id, engine, sid, text,
                                            with_permissions=True)
            self._finish(streamer, result)
        finally:
            self.ctx.busy.release(chat_id)

    # ---------- مشترك ----------

    def _stream(self, chat_id, engine, sid, text, with_permissions=False):
        st = self.ctx.state.get(chat_id)
        streamer = Streamer(self.ctx.tg, chat_id)
        stop_typing = start_typing(self.ctx.tg, chat_id)

        def on_perm(req):
            key = self.ctx.permissions.request(sid, req.get("id"))
            action = req.get("action") or "أداة"
            rows = [[{"text": "✅ مرة واحدة", "callback_data": f"perm:{key}:once"},
                     {"text": "♾️ دائمًا", "callback_data": f"perm:{key}:always"}],
                    [{"text": "⛔ رفض", "callback_data": f"perm:{key}:reject"}]]
            self.ctx.messenger.send(chat_id, f"🔐 طلب إذن: {action}",
                                    self.ctx.keyboards.kb(rows))

        try:
            result = engine.stream(
                text, session_id=sid, workdir=st["workdir"], model=st["model"],
                on_delta=lambda t: streamer.update(t),
                on_tool=lambda n, d: streamer.tool(n, d),
                on_permission=on_perm if with_permissions else None,
            )
        except Exception as exc:  # noqa: BLE001
            _log.exception("%s stream failed chat=%s", engine.kind, chat_id)
            result = StreamResult(text="", session_id=sid, error=str(exc))
        finally:
            stop_typing.set()
        return result, streamer

    @staticmethod
    def _finish(streamer, result):
        body = result.text or (f"⚠️ {result.error}" if result.error else "(لا مخرجات)")
        streamer.finish(body)
