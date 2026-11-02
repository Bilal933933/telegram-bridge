"""Composition Root: النسخ المشتركة من الحالة والخدمات، في مكان واحد."""
from bridge.application.services.busy_guard import BusyGuard
from bridge.application.services.permission_broker import PermissionBroker
from bridge.infrastructure.persistence.json_state_repository import JsonStateRepository
from bridge.shared.callback_registry import CallbackRegistry

state = JsonStateRepository()
busy_guard = BusyGuard()
permissions = PermissionBroker()
callbacks = CallbackRegistry()
