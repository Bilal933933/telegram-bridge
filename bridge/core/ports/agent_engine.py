"""عقد المحرّك (Strategy): كل محرّك ينفّذه فلا يعرف المستدعي أي محرّك يعمل."""
from __future__ import annotations

from typing import Callable, Protocol

from bridge.core.models import (
    AgentInfo,
    HistoryEntry,
    ModelInfo,
    ProjectInfo,
    SessionInfo,
    StreamResult,
)

OnDelta = Callable[[str], None]
OnTool = Callable[[str, str], None]
OnPermission = Callable[[dict], None]


class AgentEngine(Protocol):
    """المشترك بين Qoder و OpenCode. ما لا يدعمه محرّك يرفع EngineError."""

    kind: str
    supports_projects: bool
    supports_agents: bool
    supports_permissions: bool
    rich_cards: bool  # بطاقة جلسة كاملة (حالة/رموز/تكلفة) مقابل بطاقة مبسّطة

    def list_sessions(self, workdir: str, limit: int = 20) -> list[SessionInfo]:
        """جلسات مساحة عمل معيّنة، الأحدث أولًا."""
        ...

    def create_session(self, workdir: str, title: str) -> str:
        """ينشئ جلسة ويعيد معرّفها."""
        ...

    def stream(
        self,
        prompt: str,
        *,
        session_id: str | None,
        workdir: str,
        model: str | None,
        on_delta: OnDelta,
        on_tool: OnTool,
        on_permission: OnPermission | None = None,
    ) -> StreamResult:
        """يرسل رسالة ويبثّ الرد تدريجيًا حتى انتهائه."""
        ...

    def interrupt(self, session_id: str | None = None) -> bool:
        """يوقف المهمة الجارية إن وُجدت."""
        ...

    def is_active(self, session_id: str) -> bool:
        """هل الجلسة منفّذة الآن؟"""
        ...

    def list_models(self, workdir: str) -> list[str]:
        """أسماء النماذج المتاحة."""
        ...

    def history(self, session_id: str, limit: int = 40) -> list[HistoryEntry]:
        """محادثة الجلسة (الأحدث آخرًا)."""
        ...

    # اختيارية حسب القدرات
    def list_projects(self, limit: int = 15) -> list[ProjectInfo]:
        ...

    def sessions_in(self, directory: str, limit: int = 20) -> list[SessionInfo]:
        ...

    def list_agents(self, workdir: str | None = None) -> list[AgentInfo]:
        ...

    def list_model_details(self, limit: int = 40) -> list[ModelInfo]:
        ...
