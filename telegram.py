"""عميل Bot API: إرسال/تعديل/أزرار + بث لحظي بتعديل الرسائل.

بعض مزوّدي الإنترنت يحجبون عنوان api.telegram.org من الـ DNS. لذلك إذا فشل
الاتصال العادي نجرّب عناوين تيليجرام المعروفة مع إبقاء اسم النطاق (SNI)،
ثم نتذكّر أول عنوان ناجح لبقية الجلسة.
"""
import http.client
import json
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

import config
import formatting

HOST = "api.telegram.org"
FALLBACK_IPS = ("149.154.167.220", "149.154.175.50", "149.154.175.100")
PIN = {"ip": None}
SSL_CTX = ssl.create_default_context()


class _PinnedHTTPS(http.client.HTTPSConnection):
    """اتصال بعنوان IP ثابت مع SNI باسم api.telegram.org."""

    def __init__(self, ip, timeout):
        super().__init__(ip, 443, timeout=timeout, context=SSL_CTX)

    def connect(self):
        sock = socket.create_connection((self.host, self.port), self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=HOST)


def _post(path, data, timeout, ip=None):
    """→ (status, body bytes)؛ لا يرفع استثناءً على أخطاء HTTP."""
    if ip:
        conn = _PinnedHTTPS(ip, timeout)
        try:
            conn.request("POST", path, body=data,
                         headers={"Host": HOST,
                                  "Content-Type": "application/x-www-form-urlencoded"})
            resp = conn.getresponse()
            return resp.status, resp.read()
        finally:
            conn.close()
    req = urllib.request.Request("https://" + HOST + path, data=data)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


class Telegram:
    def __init__(self, token):
        self.base = f"https://api.telegram.org/bot{token}/"
        self.path = f"/bot{token}/"

    def _send_raw(self, method, data, timeout):
        path = self.path + method
        if PIN["ip"]:
            try:
                return _post(path, data, timeout, ip=PIN["ip"])
            except OSError:  # انقطع العنوان المثبّت → أعد الاكتشاف
                PIN["ip"] = None
        try:
            return _post(path, data, min(timeout, 12))
        except OSError:
            pass
        for ip in FALLBACK_IPS:
            try:
                status, body = _post(path, data, timeout, ip=ip)
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
