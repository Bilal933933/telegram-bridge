"""ربط موضوعات تيليجرام (Topics) بجلسات OpenCode: ملف JSON بكتابة ذرّية."""
from __future__ import annotations

import json
import threading

import config


class TopicStore:
    """يحفظ مجموعة الموضوعات وخريطة thread_id → جلسة."""

    def __init__(self, path=None):
        self.path = path or (config.BASE / "topics.json")
        self._lock = threading.Lock()

    def _read(self):
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def _write(self, data):
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def group(self):
        with self._lock:
            value = self._read().get("group")
        return int(value) if value else None

    def bind_group(self, chat_id):
        with self._lock:
            data = self._read()
            data["group"] = int(chat_id)
            self._write(data)

    def bind(self, thread_id, chat_id, session_id, directory=""):
        with self._lock:
            data = self._read()
            data.setdefault("topics", {})[str(thread_id)] = {
                "chat": int(chat_id),
                "session": session_id,
                "dir": directory or "",
            }
            self._write(data)

    def resolve(self, thread_id):
        """بيانات الجلسة خلف موضوع، أو None."""
        with self._lock:
            item = (self._read().get("topics") or {}).get(str(thread_id))
        return item or None

    def thread_of(self, session_id):
        """معرّف موضوع جلسة معيّنة، أو None."""
        with self._lock:
            topics = self._read().get("topics") or {}
        for thread_id, item in topics.items():
            if item.get("session") == session_id:
                return int(thread_id)
        return None
