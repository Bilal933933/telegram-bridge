"""مشاريع Qoder: مجلدات العمل من ~/.qoder/projects (قراءة فقط، بلا CLI)."""
from __future__ import annotations

import json
import os
from pathlib import Path

PROJECTS_DIR = Path.home() / ".qoder" / "projects"


def _dirs_of(path):
    """يقرأ أول سطر workspace-directories ويعيد أول مجلد، أو ''."""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except ValueError:
                    continue
                if item.get("type") == "workspace-directories":
                    dirs = item.get("directories") or []
                    return dirs[0] if dirs else ""
    except OSError:
        return ""
    return ""


def _key(path):
    return os.path.normcase(os.path.normpath(path or ""))


def _jsonl(folder):
    try:
        return [p for p in folder.glob("*.jsonl") if p.is_file()]
    except OSError:
        return []


def _mtime(path):
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def _folders(root):
    try:
        return [p for p in root.iterdir() if p.is_dir()]
    except OSError:
        return []


def list_projects(limit=15, root=None):
    """مشاريع Qoder: [{"id", "dir", "vcs", "active", "sessions"}] الأحدث أولًا."""
    root = Path(root or PROJECTS_DIR)
    out = []
    for folder in _folders(root):
        files = _jsonl(folder)
        if not files:
            continue
        newest = max(files, key=_mtime)
        directory = _dirs_of(newest)
        if not directory:
            continue
        out.append({"id": folder.name, "dir": directory, "vcs": "",
                    "active": int(_mtime(newest) * 1000), "sessions": len(files)})
    out.sort(key=lambda item: item["active"], reverse=True)
    return out[:limit] if limit else out


def session_times(directory, root=None):
    """{session_id: مدة آخر تعديل بالمللي ثانية} لجلسات مجلد عمل معيّن."""
    root = Path(root or PROJECTS_DIR)
    wanted = _key(directory)
    for folder in _folders(root):
        files = _jsonl(folder)
        if not files:
            continue
        if _key(_dirs_of(max(files, key=_mtime))) != wanted:
            continue
        return {p.stem: int(_mtime(p) * 1000) for p in files}
    return {}
