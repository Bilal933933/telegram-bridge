"""طلبات إذن الأدوات: مفتاح قصير لكل طلب مع صلاحية زمنية (TTL)."""
from __future__ import annotations

import itertools
import threading
import time


class PermissionBroker:
    def __init__(self, ttl=1800):
        self._ttl = ttl
        self._seq = itertools.count(1)
        self._pending = {}
        self._lock = threading.Lock()

    def request(self, session_id, request_id) -> str:
        """يسجّل طلبًا ويعيد مفتاحه القصير للاستخدام في callback_data."""
        with self._lock:
            key = f"p{next(self._seq)}"
            self._pending[key] = (session_id, request_id, time.time() + self._ttl)
            return key

    def resolve(self, key):
        """→ (session_id, request_id) مرة واحدة فقط، أو None إن انتهت صلاحيته."""
        with self._lock:
            item = self._pending.pop(key, None)
        if not item:
            return None
        session_id, request_id, expires = item
        if expires < time.time():
            return None
        return session_id, request_id
