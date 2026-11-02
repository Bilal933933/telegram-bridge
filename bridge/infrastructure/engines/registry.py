"""سجل المحرّكات: يحوّل نوع المحرّك إلى كائن ينفّذ عقد AgentEngine."""
from __future__ import annotations

from bridge.infrastructure.engines.opencode.engine import OpenCodeEngine
from bridge.infrastructure.engines.qoder.engine import QoderEngine

_ENGINES = {}


def get(kind):
    """يعيد نسخة واحدة (singleton) لكل محرّك."""
    engine = _ENGINES.get(kind)
    if engine is None:
        if kind == "opencode":
            engine = OpenCodeEngine()
        elif kind == "qoder":
            engine = QoderEngine()
        else:
            raise ValueError(f"محرّك غير معروف: {kind}")
        _ENGINES[kind] = engine
    return engine
