"""المشاريع: قراءة المشاريع الحقيقية وجلسات كل مشروع."""
from bridge.infrastructure.engines.registry import get as get_engine


def list_projects(limit=12):
    return get_engine("opencode").list_projects(limit)


def sessions(directory, limit=20):
    return get_engine("opencode").sessions_in(directory, limit)
