from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bridge.application.services.delivery import Delivery
from bridge.application.services.screen_tracker import ScreenTracker
from bridge.application.services.topic_service import TopicService
from bridge.application.session_service import SessionService
from bridge.infrastructure.persistence.topic_store import TopicStore
from bridge.presentation.messenger import Messenger

GROUP = -1001234567890


class FakeTG:
    def __init__(self, thread_id=77):
        self.thread_id = thread_id
        self.topics = []
        self.sent = []

    def create_topic(self, chat_id, name):
        self.topics.append((chat_id, name))
        return self.thread_id

    def send(self, chat_id, text, kb=None, html=True, thread_id=None):
        self.sent.append((chat_id, text, thread_id))
        return 1


class TopicStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "topics.json"
        self.store = TopicStore(self.path)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_group_binding_survives_reload(self) -> None:
        self.store.bind_group(GROUP)
        self.assertEqual(TopicStore(self.path).group(), GROUP)

    def test_thread_and_session_are_linked(self) -> None:
        self.store.bind(77, 5, "ses_1", r"E:\work\app")
        self.assertEqual(self.store.thread_of("ses_1"), 77)
        binding = self.store.resolve(77)
        self.assertEqual(binding["session"], "ses_1")
        self.assertEqual(binding["chat"], 5)
        self.assertEqual(binding["dir"], r"E:\work\app")

    def test_unknown_values(self) -> None:
        self.assertIsNone(self.store.group())
        self.assertIsNone(self.store.resolve(99))
        self.assertIsNone(self.store.thread_of("nope"))


class DeliveryTests(unittest.TestCase):
    def test_target_follows_current_thread(self) -> None:
        delivery = Delivery(lambda: GROUP)
        self.assertEqual(delivery.target(5), (5, None))
        delivery.begin(77)
        self.assertEqual(delivery.target(5), (GROUP, 77))
        delivery.clear()
        self.assertEqual(delivery.target(5), (5, None))

    def test_without_group_topics_are_ignored(self) -> None:
        delivery = Delivery(lambda: None)
        delivery.begin(77)
        self.assertEqual(delivery.target(5), (5, None))

    def test_screens_are_scoped_per_topic(self) -> None:
        delivery = Delivery(lambda: GROUP)
        tracker = ScreenTracker(scope=lambda: delivery.current())
        tracker.set(5, "sessions")
        delivery.begin(77)
        self.assertIsNone(tracker.get(5))
        tracker.set(5, "card")
        delivery.clear()
        self.assertEqual(tracker.get(5), "sessions")


class TopicServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = TopicStore(Path(self.tmp.name) / "topics.json")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_ensure_creates_once_and_reuses(self) -> None:
        tg = FakeTG()
        service = TopicService(tg, self.store, GROUP)
        first = service.ensure(5, "ses_abcdef", "app", r"E:\work\app")
        second = service.ensure(5, "ses_abcdef", "app", r"E:\work\app")
        self.assertEqual(first, 77)
        self.assertEqual(second, 77)
        self.assertEqual(len(tg.topics), 1)
        self.assertEqual(service.resolve(77)["session"], "ses_abcdef")
        self.assertEqual(service.thread_for("ses_abcdef"), 77)

    def test_ensure_is_off_without_group(self) -> None:
        service = TopicService(FakeTG(), self.store, 0)
        self.assertIsNone(service.ensure(5, "ses_1"))

    def test_link_points_to_the_topic(self) -> None:
        service = TopicService(FakeTG(), self.store, GROUP)
        service.ensure(5, "ses_1", "app", r"E:\work\app")
        self.assertEqual(service.link("ses_1"), "https://t.me/c/1234567890/77")

    def test_messenger_routes_into_the_topic(self) -> None:
        tg = FakeTG()
        delivery = Delivery(lambda: GROUP)
        messenger = Messenger(tg, delivery)
        messenger.send(5, "مرحبا")
        self.assertEqual(tg.sent[-1][0], 5)
        self.assertIsNone(tg.sent[-1][2])
        delivery.begin(77)
        messenger.send(5, "مرحبا")
        self.assertEqual(tg.sent[-1][0], GROUP)
        self.assertEqual(tg.sent[-1][2], 77)


class SessionTopicTests(unittest.TestCase):
    def test_create_and_open_ensure_a_topic(self) -> None:
        class Store:
            def update(self, chat_id, **changes):
                return changes

            def get(self, chat_id):
                return {"workdir": "E:/w"}

        class Engine:
            def create_session(self, directory, title):
                return "ses_abc"

            def session_info(self, sid):
                return {"location": {"directory": "E:/w"}}

        calls = []

        class Topics:
            def ensure(self, chat_id, sid, title="", directory=""):
                calls.append((chat_id, sid, title, directory))

        service = SessionService(Store(), lambda kind: Engine(), Topics())
        self.assertEqual(service.create(5, r"E:\work\app", "app"), "ses_abc")
        service.open(5, "ses_abc")
        self.assertEqual([c[1] for c in calls], ["ses_abc", "ses_abc"])
        self.assertEqual(calls[0][3], r"E:\work\app")


if __name__ == "__main__":
    unittest.main()
