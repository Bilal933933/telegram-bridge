"""هرم الأخطاء الموحّد للتطبيق.

كل خطأ متوقَّع يرثه BridgeError ويحمل رسالة آمنة تُعرض للمستخدم، بينما
التفاصيل التقنية (detail) تُسجَّل في السجل فقط ولا تُرسل إلى المحادثة.
"""
from __future__ import annotations


class BridgeError(Exception):
    """الأصل لكل الأخطاء المتوقَّعة في التطبيق."""

    default_message = "حدث خطأ غير متوقع."

    def __init__(self, user_message: str | None = None, *, detail: str | None = None) -> None:
        self.user_message: str = user_message or self.default_message
        self.detail: str | None = detail
        super().__init__(detail or self.user_message)


class ValidationError(BridgeError):
    """مدخلات غير صالحة من المستخدم (مسار، رقم، اسم نموذج...)."""

    default_message = "مدخلات غير صالحة."


class NotFoundError(BridgeError):
    """عنصر مطلوب غير موجود (جلسة، مشروع، نموذج...)."""

    default_message = "العنصر المطلوب غير موجود."


class BusyError(BridgeError):
    """الجلسة أو المحرّك مشغول بمهمة جارية."""

    default_message = "هناك مهمة قيد التنفيذ. أرسل /stop لإيقافها."


class EngineError(BridgeError):
    """فشل في أحد المحرّكات (OpenCode / Qoder)."""

    default_message = "تعذّر تنفيذ الطلب على المحرّك."
