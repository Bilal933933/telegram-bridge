"""نماذج البيانات المشتركة بين المحرّكات والواجهة."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict


class SessionInfo(TypedDict, total=False):
    """عنصر جلسة موحّد (OpenCode: id/dir/updated، Qoder: index/when)."""

    id: str
    title: str
    dir: str
    updated: float
    index: int
    when: str


class HistoryEntry(TypedDict, total=False):
    role: str
    text: str
    ts: float | None


class ProjectInfo(TypedDict, total=False):
    id: str
    dir: str
    vcs: str
    active: float
    sessions: int


class ModelInfo(TypedDict, total=False):
    id: str
    name: str
    provider: str


class AgentInfo(TypedDict, total=False):
    id: str
    name: str
    desc: str


@dataclass(frozen=True)
class StreamResult:
    """نتيجة تنفيذ رسالة واحدة على محرّك."""

    text: str
    session_id: str | None = None
    error: str | None = None
