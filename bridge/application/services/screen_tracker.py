"""آخر موضع لكل محادثة: مفتاح الشاشة التي يقف فيها المستخدم الآن."""
from __future__ import annotations

import threading
import time


class ScreenTracker:
    """يحفظ مفتاح الشاشة الحالية لكل محادثة بصلاحية زمنية."""

    def __init__(self, ttl=3600):
        self._ttl = ttl
        self._items = {}
        self._lock = threading.Lock()

    def set(self, chat_id, data) -> None:
        with self._lock:
            self._items[chat_id] = (data, time.time() + self._ttl)

    def get(self, chat_id):
        """مفتاح الشاشة الحالية، أو None إن لم تُفتح شاشة أو انتهت صلاحيتها."""
        with self._lock:
            item = self._items.get(chat_id)
            if not item:
                return None
            data, expires = item
            if expires < time.time():
                self._items.pop(chat_id, None)
                return None
            return data

    def clear(self, chat_id) -> None:
        with self._lock:
            self._items.pop(chat_id, None)
