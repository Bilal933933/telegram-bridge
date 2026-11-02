"""نقل HTTP إلى api.telegram.org مع عنوان بديل عند حجب DNS.

بعض مزوّدي الإنترنت يحجبون اسم النطاق، لذا عند فشل الاتصال العادي نجرّب
عناوين تيليجرام المعروفة مع إبقاء اسم النطاق (SNI)، ثم نتذكّر أول عنوان
ناجح لبقية الجلسة.
"""
import http.client
import socket
import ssl
import urllib.error
import urllib.request

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


def post(path, data, timeout, ip=None):
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
