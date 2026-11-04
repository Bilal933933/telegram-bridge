"""سجل المحرّكات: يحوّل نوع المحرّك إلى كائن ينفّذ عقد AgentEngine."""
from __future__ import annotations

from bridge.infrastructure.engines.opencode.engine import OpenCodeEngine
from bridge.infrastructure.engines.qoder.engine import QoderEngine

# إضافة محرّك جديد = سطر واحد هنا (الواجهة تقرأ القدرات لا النوع).
_FACTORIES = {
    "opencode": OpenCodeEngine,
    "qoder": QoderEngine,
}

_ENGINES = {}


def get(kind):
    """يعيد نسخة واحدة (singleton) لكل محرّك."""
    engine = _ENGINES.get(kind)
    if engine is None:
        factory = _FACTORIES.get(kind)
        if factory is None:
            raise ValueError(f"محرّك غير معروف: {kind}")
        engine = factory()
        _ENGINES[kind] = engine
    return engine
