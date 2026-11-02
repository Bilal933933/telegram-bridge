from __future__ import annotations

import unittest

from bridge.core.errors import BridgeError, BusyError, NotFoundError
from bridge.shared.error_boundary import GENERIC_MESSAGE, ErrorBoundary


class Recorder:
    def __init__(self) -> None:
        self.sent: list[tuple[int, str]] = []

    def __call__(self, chat_id: int, text: str) -> None:
        self.sent.append((chat_id, text))


def _raise(exc: BaseException) -> None:
    raise exc


class ErrorBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rec = Recorder()
        self.boundary = ErrorBoundary(self.rec)

    def test_success_sends_nothing(self) -> None:
        self.boundary.run(1, lambda: None)
        self.assertEqual(self.rec.sent, [])

    def test_bridge_error_sends_user_message_only(self) -> None:
        err = NotFoundError("الجلسة غير موجودة", detail="sid=abc secret-path")
        self.boundary.run(7, lambda: _raise(err))
        self.assertEqual(self.rec.sent, [(7, "⚠️ الجلسة غير موجودة")])
        self.assertNotIn("secret-path", self.rec.sent[0][1])

    def test_default_message_is_used(self) -> None:
        self.boundary.run(1, lambda: _raise(BusyError()))
        self.assertEqual(self.rec.sent, [(1, f"⚠️ {BusyError.default_message}")])

    def test_unexpected_error_is_generic_and_leaks_nothing(self) -> None:
        self.boundary.run(2, lambda: _raise(RuntimeError("token=123:ABC")))
        self.assertEqual(self.rec.sent, [(2, GENERIC_MESSAGE)])

    def test_none_chat_id_never_notifies(self) -> None:
        self.boundary.run(None, lambda: _raise(RuntimeError("x")))
        self.assertEqual(self.rec.sent, [])

    def test_notifier_failure_does_not_propagate(self) -> None:
        def broken(chat_id: int, text: str) -> None:
            raise OSError("network down")

        ErrorBoundary(broken).run(1, lambda: _raise(RuntimeError("x")))

    def test_hierarchy(self) -> None:
        self.assertTrue(issubclass(NotFoundError, BridgeError))
        self.assertTrue(issubclass(BusyError, BridgeError))


if __name__ == "__main__":
    unittest.main()
