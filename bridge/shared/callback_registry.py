"""سجل مؤقت: يخزّن بيانات الأزرار خلف مفاتيح قصيرة (حد تيليجرام 64 بايت)."""
from __future__ import annotations

import itertools
import threading
import time

TTL = 3600


class CallbackRegistry:
    def __init__(self, ttl=TTL, max_items=400):
        self._ttl = ttl
        self._max = max_items
        self._seq = itertools.count(1)
        self._data = {}
        self._lock = threading.Lock()

    def _prune(self):
        now = time.time()
        for key in [k for k, (_, exp) in self._data.items() if exp < now]:
            self._data.pop(key, None)

    def put(self, payload, ttl=None):
        key = f"k{next(self._seq)}"
        with self._lock:
            self._data[key] = (payload, time.time() + (ttl or self._ttl))
            if len(self._data) > self._max:
                self._prune()
        return key

    def get(self, key):
        with self._lock:
            item = self._data.get(key)
            if not item:
                return None
            payload, exp = item
            if exp < time.time():
                self._data.pop(key, None)
                return None
            return payload

    def drop(self, key):
        with self._lock:
            self._data.pop(key, None)
