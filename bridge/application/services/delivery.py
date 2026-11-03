"""وجهة الإرسال: نفس المكان الذي جاءت منه الرسالة (المحادثة الخاصة أو موضوعها)."""
from __future__ import annotations

import threading


class Delivery:
    """يحمل موضوع الطلب الحالي في خيطه، فلا تتسرّب الوجهة بين تحديثين متوازيين."""

    def __init__(self, group_get):
        self._group_get = group_get
        self._local = threading.local()

    def begin(self, thread_id):
        self._local.thread = thread_id

    def clear(self):
        self._local.thread = None

    def current(self):
        return getattr(self._local, "thread", None)

    def target(self, chat_id):
        """(chat_id, thread_id): داخل الموضوع نرسل للمجموعة، وإلا للمحادثة الخاصة."""
        thread = self.current()
        group = self._group_get()
        if thread and group:
            return group, thread
        return chat_id, None
