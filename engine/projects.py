"""المشاريع: قراءة المشاريع الحقيقية وجلسات كل مشروع."""
from backends import opencode as oc


def list_projects(limit=12):
    try:
        return oc.projects(limit)
    except Exception:  # noqa: BLE001
        return []


def sessions(directory, limit=20):
    try:
        return oc.sessions_in(directory, limit)
    except Exception:  # noqa: BLE001
        return []
