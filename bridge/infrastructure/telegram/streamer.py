"""عرض الرد تدريجيًا بتعديل رسالة واحدة (أو أكثر عند تجاوز الطول)."""
import time

import config
from bridge.presentation.chunker import chunks
from bridge.presentation.html_escape import esc
from bridge.presentation.markdown_to_html import to_html


class Streamer:
    def __init__(self, tg, chat_id):
        self.tg = tg
        self.chat_id = chat_id
        self.ids = []
        self.last = 0.0
        self.tool_msg = None
        self.tools = []

    def _parts(self, text):
        return [to_html(chunk) for chunk in chunks(text)]

    def update(self, text, force=False):
        now = time.time()
        if not force and now - self.last < config.STREAM_INTERVAL:
            return
        self.last = now
        htmls = self._parts(text or "…")
        for idx, body in enumerate(htmls):
            if idx < len(self.ids):
                if idx == len(htmls) - 1 or force:
                    self.tg.edit(self.chat_id, self.ids[idx], body)
            else:
                mid = self.tg.send(self.chat_id, body)
                if mid:
                    self.ids.append(mid)

    def tool(self, name, detail=""):
        line = f"⚙ {name}" + (f": {detail[:120]}" if detail else "")
        self.tools.append(line)
        recent = "\n".join(self.tools[-3:])
        body = f"<pre>{esc(recent)}</pre>"
        if self.tool_msg is None:
            self.tool_msg = self.tg.send(self.chat_id, body)
        else:
            self.tg.edit(self.chat_id, self.tool_msg, body)

    def finish(self, text, kb_markup=None):
        if not text:
            text = "(لا مخرجات)"
        htmls = self._parts(text)
        for idx, body in enumerate(htmls):
            markup = kb_markup if idx == len(htmls) - 1 else None
            if idx < len(self.ids):
                self.tg.edit(self.chat_id, self.ids[idx], body, kb=markup)
            else:
                mid = self.tg.send(self.chat_id, body, kb=markup)
                if mid:
                    self.ids.append(mid)
