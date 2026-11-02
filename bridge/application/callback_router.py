"""توجيه ضغطات الأزرار: جدول مفاتيح/بادئات → معالج، بلا شجرة if طويلة."""
from __future__ import annotations

from bridge.application.commands import (
    agent,
    change_dir,
    history,
    model,
    new_session,
    open_session,
    permission,
    project_view,
    projects,
    session_view,
    sessions,
    status,
)
from bridge.application.commands import help as help_cmd
from bridge.application.commands import switch_engine


class CallbackRouter:
    def __init__(self):
        self._exact = {}
        self._prefixes = []

    def add(self, data, handler):
        """زر بمعرّف ثابت: handler(ctx, chat_id)."""
        self._exact[data] = handler
        return self

    def add_prefix(self, prefix, handler):
        """زر بمعرّف مركّب: handler(ctx, chat_id, rest)."""
        self._prefixes.append((prefix, handler))
        return self

    def dispatch(self, ctx, chat_id, data):
        handler = self._exact.get(data)
        if handler:
            handler(ctx, chat_id)
            return True
        for prefix, handler in self._prefixes:
            if data.startswith(prefix):
                handler(ctx, chat_id, data[len(prefix):])
                return True
        return False


def _permission(ctx, chat_id, rest):
    key, _, decision = rest.partition(":")
    permission.run(ctx, chat_id, key, decision)


def build_callback_router():
    """جدول أزرار القوائم والشاشات — معرّفات قصيرة تبقى داخل حد تيليجرام."""
    return (CallbackRouter()
            .add("ph", projects.run)
            .add("sessions", sessions.run)
            .add("card", open_session.card)
            .add("new", new_session.run)
            .add("status", status.run)
            .add("help", help_cmd.run)
            .add("hist", lambda ctx, chat_id: history.all_messages(ctx, chat_id, None))
            .add("ag", agent.show)
            .add("md", model.list_opencode)
            .add_prefix("src:", switch_engine.run)
            .add_prefix("open:", open_session.from_key)
            .add_prefix("cd:", change_dir.from_button)
            .add_prefix("model:", model.set_qoder)
            .add_prefix("perm:", _permission)
            .add_prefix("pr:", project_view.run)
            .add_prefix("ps:", session_view.run)
            .add_prefix("pn:", new_session.from_project)
            .add_prefix("pb:", project_view.run)
            .add_prefix("agx:", agent.set_agent)
            .add_prefix("mdx:", model.set_opencode))
