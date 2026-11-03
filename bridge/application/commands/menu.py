"""أزرار الموضع الحالي: يعيد عرض الشاشة التي يقف فيها المستخدم."""
from __future__ import annotations

from bridge.application.commands import open_session, projects
from bridge.application.commands import help as help_cmd


def run(ctx, chat_id, arg=""):
    data = ctx.screens.get(chat_id)
    if data and ctx.callback_router.dispatch(ctx, chat_id, data):
        return
    if ctx.state.get(chat_id)["oc_session"]:
        open_session.card(ctx, chat_id)
        return
    if _has_projects(ctx):
        projects.run(ctx, chat_id)
        return
    help_cmd.run(ctx, chat_id)


def _has_projects(ctx):
    try:
        return bool(ctx.projects.list_projects(1))
    except Exception:  # noqa: BLE001 — تعذّر القراءة يعني لا شاشة مشاريع
        return False
