"""تشغيل Qoder CLI وقراءة مخرجاته النصية."""
from __future__ import annotations

import os
import re
import subprocess

import config

SESS_RE = re.compile(r"^\s*(\d+)\.\s+(.*?)\s+\(([^)]*)\)\s+\[([0-9a-fA-F-]{8,})\]\s*$")


def run(args, timeout=90):
    """→ (returncode, stdout, stderr) بلا رفع استثناء عند المهلة."""
    flags = 0x08000000 if os.name == "nt" else 0
    try:
        p = subprocess.run([config.QODER] + args, capture_output=True, timeout=timeout,
                           creationflags=flags)
    except subprocess.TimeoutExpired:
        return 1, "", "timeout"
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def parse_sessions(output):
    items = []
    for line in output.splitlines():
        m = SESS_RE.match(line)
        if m:
            items.append({"index": int(m.group(1)), "title": m.group(2),
                          "when": m.group(3), "id": m.group(4)})
    return items


def parse_models(output):
    return [ln.strip() for ln in output.splitlines()
            if ln.strip() and not ln.strip().upper().startswith("MODEL")]
