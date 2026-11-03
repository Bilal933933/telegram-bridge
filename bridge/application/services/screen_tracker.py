"""آخر موضع لكل محادثة: مفتاح الشاشة التي يقف فيها المستخدم الآن."""
from __future__ import annotations

import threading
import time


class ScreenTracker:
    """يحفظ مفتاح الشاشة الحالية لكل محادثة (أو لكل موضوع فيها) بصلاحية زمنية."""

    def __init__(self, ttl=3600, scope=None):
        self._ttl = ttl
        self._scope = scope or (lambda: None)
        self._items = {}
        self._lock = threading.Lock()

    def _key(self, chat_id):
        """المحادثة + الموضوع الحالي، فلا تختلط شاشات المواضيع بعضها ببعض."""
        return (chat_id, self._scope())

    def set(self, chat_id, data) -> None:
        with self._lock:
            self._items[self._key(chat_id)] = (data, time.time() + self._ttl)

    def get(self, chat_id):
        """مفتاح الشاشة الحالية، أو None إن لم تُفتح شاشة أو انتهت صلاحيتها."""
        key = self._key(chat_id)
        with self._lock:
            item = self._items.get(key)
            if not item:
                return None
            data, expires = item
            if expires < time.time():
                self._items.pop(key, None)
                return None
            return data

    def clear(self, chat_id) -> None:
        with self._lock:
            self._items.pop(self._key(chat_id), None)
