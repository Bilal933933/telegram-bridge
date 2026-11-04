from __future__ import annotations

import unittest
from types import SimpleNamespace

from bridge.infrastructure.telegram.poller import TelegramPoller

GROUP = -1001234567890


class _Stop(BaseException):
    """إنهاء حلقة الاستطلاع في الاختبار (لا تلتقطه معالجات الاستثناءات)."""


class _TG:
    """getUpdates: تحديث واحد في النداء الأول، ثم إيقاف الحلقة."""

    def __init__(self, updates):
        self.calls = 0
        self.sent = []
        self.answered = []
        self._updates = updates

    def call(self, method, **params):
        self.calls += 1
        if self.calls == 1:
            return {"result": self._updates}
        raise _Stop

    def send(self, chat_id, text, kb=None, html=True, thread_id=None):
        self.sent.append((chat_id, thread_id))
        return len(self.sent)

    def answer(self, callback_id, text=None):
        self.answered.append(callback_id)

    def action(self, chat_id, action="typing", thread_id=None):
        pass


def _message(chat_id, text, chat_type="private", thread_id=None, sender=42):
    message = {"chat": {"id": chat_id, "type": chat_type},
               "from": {"id": sender}, "text": text}
    if thread_id:
        message["message_thread_id"] = thread_id
    return {"update_id": 1, "message": message}


class PollerResilienceTests(unittest.TestCase):
    def _poller(self, tg, topics=None):
        ctx = SimpleNamespace(
            owner=42, tg=tg,
            topics=topics or SimpleNamespace(resolve=lambda thread: None),
            state=SimpleNamespace(update=lambda *a, **k: {}),
            delivery=SimpleNamespace(begin=lambda thread: None, clear=lambda: None),
            boundary=SimpleNamespace(run=lambda chat_id, action: action()),
            command_router=SimpleNamespace(dispatch=lambda *a: None),
            callback_router=SimpleNamespace(dispatch=lambda *a: None),
            messenger=SimpleNamespace(send=lambda *a, **k: None),
        )
        poller = TelegramPoller(ctx)
        poller._spawn = lambda chat_id, thread_id, handler, *args: handler(*args)
        return poller

    def test_a_failing_update_does_not_stop_the_polling_loop(self) -> None:
        tg = _TG([_message(42, "/status")])
        poller = self._poller(tg)
        poller._route = lambda update: (_ for _ in ()).throw(RuntimeError("boom"))
        with self.assertRaises(_Stop):
            poller.run()
        self.assertEqual(tg.calls, 2, "الحلقة توقفت بعد تحديث فاشل")

    def test_a_failing_answer_does_not_break_callback_routing(self) -> None:
        tg = _TG([])

        def boom(callback_id, text=None):
            raise OSError("offline")

        tg.answer = boom
        seen = []
        poller = self._poller(tg)
        poller._ctx.callback_router = SimpleNamespace(
            dispatch=lambda _ctx, chat_id, data: seen.append((chat_id, data)))
        poller._route({"update_id": 1, "callback_query": {
            "id": "c1", "data": "ph",
            "from": {"id": 42},
            "message": {"chat": {"id": 42, "type": "private"}},
        }})
        self.assertEqual(seen, [(42, "ph")])

    def test_topic_messages_are_bound_to_their_session(self) -> None:
        seen = []

        def resolve(thread):
            return {"chat": 42, "session": "ses_1", "dir": r"E:\w"} if thread == 7 else None

        poller = self._poller(_TG([]), SimpleNamespace(resolve=resolve))
        poller._ctx.command_router = SimpleNamespace(
            dispatch=lambda _ctx, chat_id, text: seen.append((chat_id, text)))
        poller._route(_message(GROUP, "مرحبا", chat_type="supergroup", thread_id=7))
        self.assertEqual(seen, [(42, "مرحبا")])


if __name__ == "__main__":
    unittest.main()
