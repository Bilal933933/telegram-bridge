from __future__ import annotations

import tempfile
import threading
import time
import unittest
from pathlib import Path

from bridge.application.services.busy_guard import BusyGuard
from bridge.application.services.permission_broker import PermissionBroker
from bridge.infrastructure.persistence.json_state_repository import JsonStateRepository
from bridge.shared.callback_registry import CallbackRegistry


class BusyGuardTests(unittest.TestCase):
    def test_acquire_release_cycle(self) -> None:
        guard = BusyGuard()
        self.assertTrue(guard.try_acquire(1))
        self.assertFalse(guard.try_acquire(1))
        self.assertTrue(guard.is_busy(1))
        guard.release(1)
        self.assertFalse(guard.is_busy(1))
        self.assertTrue(guard.try_acquire(1))

    def test_concurrent_acquire_has_one_winner(self) -> None:
        guard = BusyGuard()
        results: list[bool] = []
        lock = threading.Lock()
        start = threading.Barrier(16)

        def worker() -> None:
            start.wait()
            ok = guard.try_acquire(7)
            with lock:
                results.append(ok)

        threads = [threading.Thread(target=worker) for _ in range(16)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(results.count(True), 1)


class PermissionBrokerTests(unittest.TestCase):
    def test_resolve_is_single_use(self) -> None:
        broker = PermissionBroker()
        key = broker.request("ses1", "req1")
        self.assertTrue(key.startswith("p"))
        self.assertEqual(broker.resolve(key), ("ses1", "req1"))
        self.assertIsNone(broker.resolve(key))

    def test_expired_request_is_rejected(self) -> None:
        broker = PermissionBroker(ttl=0)
        key = broker.request("ses1", "req1")
        time.sleep(0.01)
        self.assertIsNone(broker.resolve(key))

    def test_unknown_key(self) -> None:
        self.assertIsNone(PermissionBroker().resolve("p404"))


class CallbackRegistryTests(unittest.TestCase):
    def test_put_get_drop(self) -> None:
        reg = CallbackRegistry()
        key = reg.put({"sid": "s1"})
        self.assertEqual(reg.get(key), {"sid": "s1"})
        reg.drop(key)
        self.assertIsNone(reg.get(key))

    def test_ttl_expiry(self) -> None:
        reg = CallbackRegistry(ttl=0)
        key = reg.put({"a": 1})
        time.sleep(0.01)
        self.assertIsNone(reg.get(key))


class JsonStateRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = JsonStateRepository(Path(self.tmp.name) / "state.json")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_defaults_when_empty(self) -> None:
        view = self.repo.get(5)
        self.assertEqual(view["src"], "qoder")
        self.assertIsNone(view["session_id"])

    def test_update_routes_keys_to_their_engine(self) -> None:
        self.repo.update(5, src="opencode", oc_session="ses_1", workdir="/p")
        self.repo.update(5, session_id="q1", model="m1")
        view = self.repo.get(5)
        self.assertEqual(view["src"], "opencode")
        self.assertEqual(view["oc_session"], "ses_1")
        self.assertEqual(view["session_id"], "q1")
        self.assertEqual(view["model"], "m1")

    def test_switch_changes_active_engine(self) -> None:
        self.repo.switch(5, "opencode")
        self.assertEqual(self.repo.get(5)["src"], "opencode")

    def test_ns_and_summary_expose_both_engines(self) -> None:
        self.repo.update(5, workdir="/w")
        self.assertEqual(self.repo.ns(5, "qoder")["workdir"], "/w")
        summary = self.repo.summary(5)
        self.assertIn("qoder", summary)
        self.assertIn("opencode", summary)

    def test_legacy_flat_entry_is_migrated(self) -> None:
        path = Path(self.tmp.name) / "state.json"
        path.write_text(
            '{"9": {"src": "opencode", "workdir": "/old", "oc_session": "ses_9"}}',
            encoding="utf-8",
        )
        view = self.repo.get(9)
        self.assertEqual(view["src"], "opencode")
        self.assertEqual(view["oc_session"], "ses_9")
        self.assertEqual(view["workdir"], "/old")


if __name__ == "__main__":
    unittest.main()
