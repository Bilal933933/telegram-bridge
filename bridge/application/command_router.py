"""أوامر المحادثة: جدول مطابِق → معالج (إضافة أمر لا تعدّل الموجّه)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from bridge.application.commands import (
    agent,
    change_dir,
    history,
    model,
    new_session,
    open_session,
    projects,
    prompt,
    sessions,
    status,
    stop,
    switch_engine,
)
from bridge.application.commands import help as help_cmd


@dataclass(frozen=True)
class Command:
    name: str
    match: Callable[[str, str], bool]  # (low, text) -> bool
    run: Callable[..., None]           # (ctx, chat_id, arg)


class CommandRouter:
    def __init__(self, commands):
        self._commands = list(commands)
        self._fallback = None

    def set_fallback(self, handler):
        """ما لا يطابق أي أمر يُعدّ رسالة حرّة."""
        self._fallback = handler

    def dispatch(self, ctx, chat_id, text):
        low = text.strip().lower()
        for cmd in self._commands:
            if cmd.match(low, text):
                cmd.run(ctx, chat_id, self._arg(cmd, text))
                return True
        if self._fallback:
            self._fallback(ctx, chat_id, text)
            return True
        return False

    @staticmethod
    def _arg(cmd, text):
        if " " not in text:
            return ""
        return text[len(cmd.name):].strip() if text.lower().startswith(cmd.name) else \
            text.split(" ", 1)[1].strip()


def _exact(*names):
    return lambda low, text: low in names


def _prefixed(name):
    """مطابقة اسم الأمر وحده أو متبوعًا بمسافة (لا يلتقط «/opener»)."""
    return lambda low, text: low == name or low.startswith(name + " ")


def build_command_router():
    """كل سطر أمر → معالجه، وما لا يطابق يُمرّر كرسالة حرّة."""
    router = CommandRouter([
        Command("/help", _exact("/start", "/help", "/menu"), help_cmd.run),
        Command("/src", _prefixed("/src"), switch_engine.run),
        Command("/projects", _exact("/projects"), projects.run),
        Command("/sessions", _exact("/sessions"), sessions.run),
        Command("/new", _exact("/new"), new_session.run),
        Command("/status", _exact("/status"), status.run),
        Command("/stop", _exact("/stop"), stop.run),
        Command("/history", _prefixed("/history"), history.run),
        Command("/open", _prefixed("/open"), open_session.run),
        Command("/cd", _prefixed("/cd"), change_dir.run),
        Command("/model", _prefixed("/model"), model.run),
        Command("/agent", _exact("/agent"), agent.run),
    ])
    router.set_fallback(prompt.run)
    return router
