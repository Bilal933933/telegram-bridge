"""إرسال نص للمحادثة: تحويل + تقسيم + إرسال (لا يعرف من أين جاء النص)."""
from __future__ import annotations

from bridge.presentation.chunker import chunks
from bridge.presentation.markdown_to_html import to_html


class Messenger:
    def __init__(self, tg):
        self._tg = tg

    def send(self, chat_id, text, keyboard=None):
        parts = [to_html(c) for c in chunks(text or "…")]
        for idx, body in enumerate(parts):
            last = idx == len(parts) - 1
            self._tg.send(chat_id, body, kb=keyboard if last else None)
