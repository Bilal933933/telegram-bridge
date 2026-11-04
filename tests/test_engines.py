from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

from bridge.application.commands import project_view
from bridge.application.session_service import ProjectService
from bridge.infrastructure.engines.qoder import projects as qprojects
from bridge.presentation import screens


def _write_session(folder, sid, directory, mtime=None):
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{sid}.jsonl"
    lines = [
        {"type": "workspace-directories", "sessionId": sid, "directories": [directory]},
        {"type": "user", "message": {"content": "hi"}},
    ]
    path.write_text("\n".join(json.dumps(x) for x in lines), encoding="utf-8")
    if mtime is not None:
        import os
        os.utime(path, (mtime, mtime))
    return path


class QoderProjectsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        now = time.time()
        _write_session(self.root / "E--heard-old", "s1", r"E:\heard\old", now - 7200)
        _write_session(self.root / "E--heard-new", "s2", r"E:\heard\new", now)
        _write_session(self.root / "E--heard-new", "s3", r"E:\heard\new", now - 60)
        (self.root / "broken").mkdir()
        (self.root / "broken" / "x.jsonl").write_text("not json\n", encoding="utf-8")
        (self.root / "empty").mkdir()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_projects_are_read_from_session_files(self) -> None:
        items = qprojects.list_projects(root=self.root)
        self.assertEqual([p["dir"] for p in items], [r"E:\heard\new", r"E:\heard\old"])
        self.assertEqual(items[0]["sessions"], 2)
        self.assertEqual(items[0]["id"], "E--heard-new")

    def test_broken_and_empty_folders_are_skipped(self) -> None:
        ids = [p["id"] for p in qprojects.list_projects(root=self.root)]
        self.assertNotIn("broken", ids)
        self.assertNotIn("empty", ids)

    def test_session_times_match_the_directory(self) -> None:
        times = qprojects.session_times(r"E:\heard\new", root=self.root)
        self.assertEqual(sorted(times), ["s2", "s3"])
        self.assertGreater(times["s2"], times["s3"])

    def test_limit_and_missing_directory(self) -> None:
        self.assertEqual(len(qprojects.list_projects(limit=1, root=self.root)), 1)
        self.assertEqual(qprojects.session_times(r"E:\nope", root=self.root), {})


class _Engine:
    def __init__(self, kind, rich=False, projects=None, sessions=None):
        self.kind = kind
        self.supports_projects = True
        self.rich_cards = rich
        self._projects = projects or []
        self._sessions = sessions or []

    def list_projects(self, limit=15):
        return self._projects[:limit]

    def sessions_in(self, directory, limit=20):
        return self._sessions[:limit]


class ProjectServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engines = {
            "opencode": _Engine("opencode", True, [{"id": "a", "dir": "E:/oc"}],
                                [{"id": "s1", "title": "t", "updated": 0}]),
            "qoder": _Engine("qoder", False, [{"id": "b", "dir": "E:/q"}],
                             [{"id": "s2", "title": "t2", "updated": 0}]),
        }
        self.state = SimpleNamespace(get=lambda chat_id: {"src": "qoder"})
        self.service = ProjectService(self.state, self.engines.get)

    def test_lists_follow_the_active_engine(self) -> None:
        self.assertEqual(self.service.list_projects(5)[0]["dir"], "E:/q")
        self.assertEqual(self.service.sessions(5, "E:/q")[0]["id"], "s2")
        self.assertFalse(self.service.rich_cards(5))
        self.state.get = lambda chat_id: {"src": "opencode"}
        self.assertEqual(self.service.list_projects(5)[0]["dir"], "E:/oc")
        self.assertTrue(self.service.rich_cards(5))

    def test_engine_without_projects_returns_empty(self) -> None:
        self.engines["qoder"].supports_projects = False
        self.assertEqual(self.service.list_projects(5), [])

    def test_failures_do_not_break_the_screen(self) -> None:
        def boom(*args, **kwargs):
            raise RuntimeError("down")

        self.engines["qoder"].list_projects = boom
        self.engines["qoder"].sessions_in = boom
        self.assertEqual(self.service.list_projects(5), [])
        self.assertEqual(self.service.sessions(5, "E:/q"), [])


class OpenButtonTests(unittest.TestCase):
    def _ctx(self, rich):
        return SimpleNamespace(
            projects=SimpleNamespace(rich_cards=lambda chat_id: rich,
                                     active=lambda chat_id: "qoder"),
            callbacks=SimpleNamespace(put=lambda payload: "K"),
        )

    def test_rich_engine_opens_the_session_card(self) -> None:
        button = project_view._open_button(self._ctx(True), 5, "E:/w", {"id": "s1"})
        self.assertEqual(button, "ps:K")

    def test_plain_engine_opens_the_session_directly(self) -> None:
        button = project_view._open_button(self._ctx(False), 5, "E:/w", {"id": "s1"})
        self.assertEqual(button, "open:K")


class EngineTextTests(unittest.TestCase):
    def setUp(self) -> None:
        self.summary = {
            "active": "qoder",
            "opencode": {"workdir": r"E:\a", "oc_session": "ses_oc_12345678"},
            "qoder": {"workdir": r"E:\b", "session_id": "9f8e7d6c5b4a", "model": "qfmodel"},
        }

    def test_active_line_mentions_only_the_active_engine(self) -> None:
        line = screens.active_engine_text(self.summary, "qoder")
        self.assertIn("Qoder", line)
        self.assertNotIn("OpenCode", line)
        self.assertIn("qfmodel", line)

    def test_projects_header_names_the_engine(self) -> None:
        text = screens.projects_text([{"dir": r"E:\b", "active": 0, "sessions": 3}], "qoder")
        self.assertIn("Qoder", text)
        self.assertIn("3 جلسة", text)


if __name__ == "__main__":
    unittest.main()
