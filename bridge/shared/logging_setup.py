"""إعداد موحّد للتسجيل (logging) بدل دالة log اليدوية.

الإخراج إلى stdout بالصيغة نفسها السابقة، فيبقى سكربت start-bridge.ps1
(الذي يوجّه stdout إلى bridge.log) يعمل دون تغيير.
"""
from __future__ import annotations

import logging
import sys

_ROOT_NAME = "bridge"
_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging(level: int = logging.INFO) -> None:
    """يهيّئ مسجّل التطبيق مرة واحدة (آمن عند الاستدعاء المتكرر)."""
    root = logging.getLogger(_ROOT_NAME)
    if root.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_FORMAT, _DATE_FORMAT))
    root.addHandler(handler)
    root.setLevel(level)
    root.propagate = False


def get_logger(name: str) -> logging.Logger:
    """يعيد مسجّلًا فرعيًا تحت مسار bridge.*"""
    return logging.getLogger(f"{_ROOT_NAME}.{name}")
