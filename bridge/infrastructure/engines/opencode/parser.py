"""قراءة رسائل OpenCode: النص والأدوات داخل رسالة واحدة."""
from __future__ import annotations


def text_of(msg):
    parts = []
    for part in msg.get("content") or []:
        if part.get("type") == "text" and part.get("text"):
            parts.append(part["text"])
    return "\n".join(parts).strip()


def tools_of_pairs(msg):
    out = []
    for part in msg.get("content") or []:
        if part.get("type") in ("text", "reasoning"):
            continue
        name = part.get("tool") or part.get("name") or part.get("type")
        out.append((name, ""))
    return out


def tools_of(msg):
    return [name for name, _ in tools_of_pairs(msg)]
