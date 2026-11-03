"""عميل Bot API: استدعاء الأساليب وإرسال/تعديل الرسائل فقط."""
import json
import time
import urllib.error
import urllib.parse

from bridge.infrastructure.telegram.transport import FALLBACK_IPS, PIN, post
from bridge.presentation.chunker import plain


class Telegram:
    def __init__(self, token):
        self.base = f"https://api.telegram.org/bot{token}/"
        self.path = f"/bot{token}/"

    def _send_raw(self, method, data, timeout):
        path = self.path + method
        if PIN["ip"]:
            try:
                return post(path, data, timeout, ip=PIN["ip"])
            except OSError:  # انقطع العنوان المثبّت → أعد الاكتشاف
                PIN["ip"] = None
        try:
            return post(path, data, min(timeout, 12))
        except OSError:
            pass
        for ip in FALLBACK_IPS:
            try:
                status, body = post(path, data, timeout, ip=ip)
            except OSError:
                continue
            PIN["ip"] = ip
            return status, body
        raise OSError("تعذّر الوصول إلى api.telegram.org")

    def call(self, method, **params):
        data = urllib.parse.urlencode(params).encode()
        for attempt in range(3):
            status, raw = self._send_raw(method, data, 70)
            body = raw.decode("utf-8", "replace")
            if status == 200:
                return json.loads(body)
            if status == 429:
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
                raise urllib.error.HTTPError(self.base + method, status, body[:200],
                                             None, None)
            time.sleep(1)
        return {}

    def send(self, chat_id, text, kb=None, html=True, thread_id=None):
        params = {"chat_id": chat_id, "text": text, "disable_web_page_preview": "true"}
        if thread_id:
            params["message_thread_id"] = thread_id
        if html:
            params["parse_mode"] = "HTML"
        if kb:
            params["reply_markup"] = json.dumps(kb, ensure_ascii=False)
        try:
            res = self.call("sendMessage", **params)
        except ValueError:
            params.pop("parse_mode", None)
            params["text"] = plain(text)
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
            params["text"] = plain(text)
            self.call("editMessageText", **params)

    def action(self, chat_id, action="typing", thread_id=None):
        params = {"chat_id": chat_id, "action": action}
        if thread_id:
            params["message_thread_id"] = thread_id
        try:
            self.call("sendChatAction", **params)
        except Exception:  # noqa: BLE001
            pass

    def create_topic(self, chat_id, name):
        """ينشئ موضوعًا في مجموعة Topic-enabled ويعيد message_thread_id."""
        res = self.call("createForumTopic", chat_id=chat_id, name=name[:128])
        return (res.get("result") or {}).get("message_thread_id")

    def answer(self, callback_id, text=None):
        try:
            self.call("answerCallbackQuery", callback_query_id=callback_id, text=text or "")
        except Exception:  # noqa: BLE001
            pass
