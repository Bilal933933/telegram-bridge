from __future__ import annotations

import time
import unittest
from types import SimpleNamespace

from bridge.application.callback_router import CallbackRouter
from bridge.application.command_router import (
    MENU_BUTTONS,
    Command,
    CommandRouter,
    _button,
    _exact,
    _prefixed,
    build_command_router,
)
from bridge.application.commands import menu, new_session, projects, sessions, status
from bridge.application.services.screen_tracker import ScreenTracker
from bridge.presentation.keyboards import (
    LBL_MENU,
    LBL_NEW,
    LBL_PROJECTS,
    LBL_SESSIONS,
    LBL_STATUS,
)


class ScreenTrackerTests(unittest.TestCase):
    def test_set_get_clear(self) -> None:
        tracker = ScreenTracker()
        self.assertIsNone(tracker.get(1))
        tracker.set(1, "ps:k1")
        self.assertEqual(tracker.get(1), "ps:k1")
        tracker.clear(1)
        self.assertIsNone(tracker.get(1))

    def test_chats_are_isolated(self) -> None:
        tracker = ScreenTracker()
        tracker.set(1, "ph")
        tracker.set(2, "card")
        self.assertEqual(tracker.get(1), "ph")
        self.assertEqual(tracker.get(2), "card")

    def test_expired_screen_is_dropped(self) -> None:
        tracker = ScreenTracker(ttl=0)
        tracker.set(1, "ph")
        time.sleep(0.01)
        self.assertIsNone(tracker.get(1))


class CommandRouterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.router = CommandRouter([
            Command("/open", _prefixed("/open"),
                    lambda ctx, chat, arg: self.calls.append(("open", arg))),
            Command("/status", _exact("/status"),
                    lambda ctx, chat, arg: self.calls.append(("status", arg))),
        ])
        self.router.set_fallback(lambda ctx, chat, text: self.calls.append(("prompt", text)))

    def test_prefix_with_argument(self) -> None:
        self.router.dispatch(None, 1, "/open 3")
        self.assertEqual(self.calls, [("open", "3")])

    def test_prefix_without_argument(self) -> None:
        self.router.dispatch(None, 1, "/open")
        self.assertEqual(self.calls, [("open", "")])

    def test_similar_prefix_is_not_a_command(self) -> None:
        self.router.dispatch(None, 1, "/opener")
        self.assertEqual(self.calls, [("prompt", "/opener")])

    def test_exact_command(self) -> None:
        self.router.dispatch(None, 1, "/status")
        self.assertEqual(self.calls, [("status", "")])

    def test_free_text_goes_to_fallback(self) -> None:
        self.router.dispatch(None, 1, "مرحبا")
        self.assertEqual(self.calls, [("prompt", "مرحبا")])


class RouterTableTests(unittest.TestCase):
    def test_menu_command_and_buttons_are_registered(self) -> None:
        router = build_command_router()
        by_name = {cmd.name: cmd.run for cmd in router._commands}
        self.assertIs(by_name["/menu"], menu.run)
        expected = {
            LBL_PROJECTS: projects.run,
            LBL_SESSIONS: sessions.run,
            LBL_NEW: new_session.run,
            LBL_MENU: menu.run,
            LBL_STATUS: status.run,
        }
        for label, handler in expected.items():
            self.assertIs(by_name[label], handler)
        self.assertEqual(len(by_name), len(router._commands))

    def test_button_predicate_ignores_slash_commands(self) -> None:
        match = _button(LBL_PROJECTS)
        self.assertTrue(match(LBL_PROJECTS.lower(), LBL_PROJECTS))
        self.assertFalse(match("/projects", "/projects"))
        self.assertEqual(len(MENU_BUTTONS), 5)


class CallbackRouterMemoryTests(unittest.TestCase):
    def test_only_screens_are_remembered(self) -> None:
        router = (CallbackRouter()
                  .add("ph", lambda ctx, chat: None)
                  .add_prefix("pr:", lambda ctx, chat, rest: None)
                  .add_prefix("mdx:", lambda ctx, chat, rest: None))
        ctx = SimpleNamespace(screens=ScreenTracker())
        router.dispatch(ctx, 7, "mdx:k1")
        self.assertIsNone(ctx.screens.get(7))
        router.dispatch(ctx, 7, "pr:k2")
        self.assertEqual(ctx.screens.get(7), "pr:k2")
        router.dispatch(ctx, 7, "ph")
        self.assertEqual(ctx.screens.get(7), "ph")

    def test_unknown_data_is_ignored(self) -> None:
        router = CallbackRouter()
        self.assertFalse(router.dispatch(SimpleNamespace(screens=ScreenTracker()), 7, "nope"))


if __name__ == "__main__":
    unittest.main()
