"""عميل Bot API: إرسال/تعديل/أزرار + بث لحظي بتعديل الرسائل."""
import json
import time
import urllib.error
import urllib.parse
import urllib.request

import config
import formatting


class Telegram:
    def __init__(self, token):
        self.base = f"https://api.telegram.org/bot{token}/"

    def call(self, method, **params):
        data = urllib.parse.urlencode(params).encode()
        for attempt in range(3):
            try:
                req = urllib.request.Request(self.base + method, data=data)
                with urllib.request.urlopen(req, timeout=70) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", "replace")
                if exc.code == 429:
                    try:
                        wait = json.loads(body)["parameters"]["retry_after"]
                    except Exception:  # noqa: BLE001
                        wait = 3
                    time.sleep(min(wait, 30))
                    continue
                if "message is not modified" in body:
                    return {"ok": True}
                if "can't parse entities" in body:
                    raise ValueError("parse")
                if attempt == 2:
                    raise
                time.sleep(1)
        return {}

    def send(self, chat_id, text, kb=None, html=True):
        params = {"chat_id": chat_id, "text": text, "disable_web_page_preview": "true"}
        if html:
            params["parse_mode"] = "HTML"
        if kb:
            params["reply_markup"] = json.dumps(kb, ensure_ascii=False)
        try:
            res = self.call("sendMessage", **params)
        except ValueError:
            params.pop("parse_mode", None)
            params["text"] = formatting.plain(text)
            res = self.call("sendMessage", **params)
        return (res.get("result") or {}).get("message_id")

    def edit(self, chat_id, message_id, text, kb=None):
        params = {"chat_id": chat_id, "message_id": message_id, "text": text,
                  "parse_mode": "HTML", "disable_web_page_preview": "true"}
        if kb:
            params["reply_markup"] = json.dumps(kb, ensure_ascii=False)
        try:
            self.call("editMessageText", **params)
        except ValueError:
            params.pop("parse_mode", None)
            params["text"] = formatting.plain(text)
            self.call("editMessageText", **params)

    def action(self, chat_id, action="typing"):
        try:
            self.call("sendChatAction", chat_id=chat_id, action=action)
        except Exception:  # noqa: BLE001
            pass

    def answer(self, callback_id, text=None):
        try:
            self.call("answerCallbackQuery", callback_query_id=callback_id, text=text or "")
        except Exception:  # noqa: BLE001
            pass


def kb(rows):
    return {"inline_keyboard": rows}


class Streamer:
    """يعرض الرد تدريجيًا بتعديل رسالة واحدة (أو أكثر عند الطول)."""

    def __init__(self, tg, chat_id):
        self.tg = tg
        self.chat_id = chat_id
        self.ids = []
        self.last = 0.0
        self.tool_msg = None
        self.tools = []

    def _parts(self, text):
        return [formatting.to_html(chunk) for chunk in formatting.chunks(text)]

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
        body = f"<pre>{formatting.esc(recent)}</pre>"
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
