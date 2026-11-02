"""المعالج العام الموحّد للأخطاء (مكافئ Global Exception Filter).

نقطة واحدة تلتقط ما يتسرّب من أي معالج، فلا تموت الخيوط بصمت:
- BridgeError   → تحذير في السجل + رسالة المستخدم الآمنة.
- أي استثناء آخر → سجل كامل بالـ stack trace + رسالة عامة بلا تسريب داخلي.
"""
from __future__ import annotations

from collections.abc import Callable

from bridge.core.errors import BridgeError
from bridge.shared.logging_setup import get_logger

# (chat_id, text) → يرسل نص الخطأ للمستخدم
Notifier = Callable[[int, str], None]

GENERIC_MESSAGE = "⚠️ حدث خطأ داخلي. سُجّل في السجل للمراجعة."

_log = get_logger("error_boundary")


class ErrorBoundary:
    def __init__(self, notify: Notifier) -> None:
        self._notify = notify

    def run(self, chat_id: int | None, action: Callable[[], None]) -> None:
        """ينفّذ action ويحوّل أي استثناء إلى سجل + إشعار، دون أن يرفع شيئًا."""
        try:
            action()
        except BridgeError as exc:
            _log.warning("BridgeError chat=%s: %s (detail=%s)", chat_id, exc.user_message, exc.detail)
            self._safe_notify(chat_id, f"⚠️ {exc.user_message}")
        except Exception:  # noqa: BLE001 — النقطة الوحيدة المقصودة لالتقاط كل شيء
            _log.exception("unhandled error chat=%s", chat_id)
            self._safe_notify(chat_id, GENERIC_MESSAGE)

    def _safe_notify(self, chat_id: int | None, text: str) -> None:
        if chat_id is None:
            return
        try:
            self._notify(chat_id, text)
        except Exception:  # noqa: BLE001 — فشل الإشعار لا يجب أن يُسقط الخيط
            _log.exception("failed to notify chat=%s", chat_id)
