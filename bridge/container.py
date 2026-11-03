"""Composition Root: السياق الواحد الذي تمرّره معالجات الأوامر، وكل ما فيه جاهز."""
from __future__ import annotations

import config
from bridge.application.callback_router import build_callback_router
from bridge.application.command_router import build_command_router
from bridge.application.services.busy_guard import BusyGuard
from bridge.application.services.permission_broker import PermissionBroker
from bridge.application.services.prompt_runner import PromptRunner
from bridge.application.services.screen_tracker import ScreenTracker
from bridge.application.session_service import ProjectService, SessionService
from bridge.infrastructure.engines.registry import get as get_engine
from bridge.infrastructure.persistence.json_state_repository import JsonStateRepository
from bridge.presentation.keyboards import Keyboards
from bridge.presentation.messenger import Messenger
from bridge.shared.callback_registry import CallbackRegistry
from bridge.shared.error_boundary import ErrorBoundary


class Engines:
    """قراءة المحرّكات من السجل (بلا حالة هنا)."""

    @staticmethod
    def get(kind):
        return get_engine(kind)


class Context:
    """كل تبعيات طبقة التطبيق: تُبنى مرة واحدة وتُحقن في كل معالج."""

    def __init__(self, tg, owner, state_path=None):
        self.tg = tg
        self.owner = owner
        self.messenger = Messenger(tg)
        self.state = JsonStateRepository(state_path)
        self.busy = BusyGuard()
        self.permissions = PermissionBroker()
        self.callbacks = CallbackRegistry()
        self.screens = ScreenTracker()
        self.boundary = ErrorBoundary(self._notify_owner)
        self.engines = Engines()
        self.sessions = SessionService(self.state, self.engines.get)
        self.projects = ProjectService(self.engines.get)
        self.keyboards = Keyboards()
        self.runner = PromptRunner(self)
        self.command_router = build_command_router()
        self.callback_router = build_callback_router()

    def _notify_owner(self, chat_id, text):
        """إشعار الأخطاء للمالك فقط."""
        if chat_id == self.owner:
            self.messenger.send(chat_id, text)
