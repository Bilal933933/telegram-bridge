"""قفل «مهمة جارية» لكل محادثة — فحص وحيازة في عملية واحدة (ذرّية)."""
from __future__ import annotations

import threading


class BusyGuard:
    def __init__(self):
        self._busy = set()
        self._lock = threading.Lock()

    def try_acquire(self, chat_id) -> bool:
        """يحجز المحادثة إن كانت حرّة ويعيد نجاح الحجز."""
        with self._lock:
            if chat_id in self._busy:
                return False
            self._busy.add(chat_id)
            return True

    def release(self, chat_id) -> None:
        with self._lock:
            self._busy.discard(chat_id)

    def is_busy(self, chat_id) -> bool:
        with self._lock:
            return chat_id in self._busy
