"""إرسال نص للمحادثة: تحويل + تقسيم + إرسال إلى وجهة الطلب الحالي."""
from __future__ import annotations

from bridge.presentation.chunker import chunks
from bridge.presentation.markdown_to_html import to_html


class Messenger:
    def __init__(self, tg, delivery):
        self._tg = tg
        self._delivery = delivery

    def send(self, chat_id, text, keyboard=None):
        chat, thread = self._delivery.target(chat_id)
        parts = [to_html(c) for c in chunks(text or "…")]
        for idx, body in enumerate(parts):
            last = idx == len(parts) - 1
            self._tg.send(chat, body, kb=keyboard if last else None, thread_id=thread)
