"""عقد حفظ حالة كل محادثة (يمكن استبدال JSON بـ SQLite دون مساس بالمنطق)."""
from __future__ import annotations

from typing import Protocol


class StateRepository(Protocol):
    def get(self, chat_id: int) -> dict:
        """عرض مسطّح للمحرّك النشط."""
        ...

    def ns(self, chat_id: int, engine: str) -> dict:
        """حزمة محرّك معيّن (workdir/session/model...)."""
        ...

    def entry(self, chat_id: int) -> dict:
        """الحزمة الكاملة: المحرّك النشط + حزمتاه."""
        ...

    def update(self, chat_id: int, **changes) -> dict:
        """يحدّث حقولًا ويعيد العرض المسطّح."""
        ...

    def switch(self, chat_id: int, engine: str) -> dict:
        """يبدّل المحرّك النشط."""
        ...

    def summary(self, chat_id: int) -> dict:
        """حزمتا المحرّكين + النشط (لعرض /status)."""
        ...
