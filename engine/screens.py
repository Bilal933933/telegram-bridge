"""رسم شاشات المحاكاة كنص Markdown جاهز لتيليجرام."""
import os
import time

from bridge.infrastructure.engines.opencode.parser import text_of, tools_of


def folder(path):
    path = (path or "").rstrip("\\/")
    return os.path.basename(path) or path or "—"


def short_id(sid):
    return (sid or "")[-6:]


def num(value):
    try:
        value = int(value or 0)
    except (TypeError, ValueError):
        return "0"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1000:
        return f"{value / 1000:.1f}k"
    return str(value)


def ago(ms):
    if not ms:
        return "—"
    delta = max(0, int(time.time() - ms / 1000))
    if delta < 60:
        return "الآن"
    if delta < 3600:
        return f"قبل {delta // 60} د"
    if delta < 86400:
        return f"قبل {delta // 3600} س"
    return f"قبل {delta // 86400} ي"


def clock(ms):
    if not ms:
        return "—"
    return time.strftime("%H:%M", time.localtime(ms / 1000))


# ---------- الشاشات ----------

def projects_text(items):
    lines = [f"🗂 **المشاريع** — {len(items)}", ""]
    for p in items[:10]:
        git = " · git" if p.get("vcs") else ""
        lines.append(f"• **{folder(p['dir'])}**{git} · {ago(p['active'])}")
        lines.append(f"   `{p['dir']}`")
    return "\n".join(lines)


def project_text(directory, sessions):
    git = _git_branch(directory)
    lines = [f"📁 **{folder(directory)}**",
             f"`{directory}`",
             f"{'🌿 ' + git if git else '📄 بلا git'} · 💬 {len(sessions)} جلسة", ""]
    if not sessions:
        lines.append("لا توجد جلسات بعد — أنشئ واحدة.")
    else:
        for i, s in enumerate(sessions[:8], 1):
            lines.append(f"{i}. {s['title'][:40]} · {ago(s['updated'])}")
    return "\n".join(lines)


def session_text(info, is_busy, pending=0):
    model = (info.get("model") or {})
    tokens = info.get("tokens") or {}
    cache = (tokens.get("cache") or {}).get("read") or 0
    agent = info.get("agent") or (info.get("model") or {}).get("agent") or "build"
    state_str = "⏳ تعمل الآن" if is_busy else "✅ خاملة"
    title = info.get("title") or "(بدون عنوان)"
    lines = [
        f"💬 **{title}**",
        f"🆔 `{info.get('id', '')}`",
        f"📁 {folder((info.get('location') or {}).get('directory'))}",
        f"🧠 {model.get('id') or '—'} · 🤖 {agent}",
        f"🪙 {num(tokens.get('input'))} داخل / {num(tokens.get('output'))} خارج"
        + (f" · 💾 {num(cache)}" if cache else ""),
        f"💰 ${float(info.get('cost') or 0):.4f} · {state_str}",
        f"🕒 آخر تحديث {clock((info.get('time') or {}).get('updated'))}",
    ]
    if pending:
        lines.append(f"🔐 **{pending} طلب إذن معلّق**")
    return "\n".join(lines)


def _message_block(msg, with_tools=True):
    kind = msg.get("type")
    if kind == "user":
        body = (msg.get("text") or "").strip()
        return f"👤 {body}" if body else ""
    if kind == "assistant":
        parts = []
        body = text_of(msg)
        if body:
            parts.append(f"🤖 {body}")
        if with_tools:
            tools = tools_of(msg)
            for name in tools[:4]:
                parts.append(f"⚙ {name}")
            if len(tools) > 4:
                parts.append(f"⚙ … +{len(tools) - 4}")
        error = msg.get("error")
        if error:
            parts.append(f"⚠️ {(error.get('message') if isinstance(error, dict) else error)}")
        return "\n".join(parts)
    return ""


def history(ctx, limit=40, with_tools=True):
    msgs = ctx or []
    if limit:
        msgs = msgs[-limit:]
    blocks = [b for b in (_message_block(m, with_tools) for m in msgs) if b]
    return "\n\n".join(blocks)


def talk_count(ctx):
    return sum(1 for m in ctx or [] if _message_block(m, with_tools=False))


def tail(ctx, limit=10, max_len=700):
    """آخر الرسائل المفيدة؛ وإن كانت كلها أدوات يعرض آخرها كسطر واحد."""
    msgs = ctx or []
    blocks = []
    for msg in reversed(msgs):
        block = _message_block(msg, with_tools=False)
        if not block:
            continue
        if len(block) > max_len:
            block = block[:max_len].rstrip() + "…"
        blocks.append(block)
        if len(blocks) >= limit:
            break
    if blocks:
        blocks.reverse()
        return "\n\n".join(blocks)
    names = []
    for msg in reversed(msgs):
        names = tools_of(msg) + names
        if len(names) >= 3:
            break
    return ("⚙ آخر الأدوات: " + "، ".join(names[-3:])) if names else ""


def history_entries(entries, limit=40):
    """تاريخ محفوظ محليًا (Qoder) → نص تيليجرام."""
    items = entries[-limit:] if limit else entries
    blocks = []
    for item in items:
        text = (item.get("text") or "").strip()
        if text:
            icon = "👤" if item.get("role") == "user" else "🤖"
            blocks.append(f"{icon} {text}")
    return "\n\n".join(blocks)


def qoder_card(st, sid, title=""):
    return "\n".join([
        f"💬 **{title or 'جلسة Qoder'}**",
        f"🆔 `{sid}`",
        f"📁 {folder(st['workdir'])}",
        f"🧠 {st['model'] or '(افتراضي)'}",
    ])


def _git_branch(directory):
    head = os.path.join(directory or "", ".git", "HEAD")
    try:
        with open(head, "r", encoding="utf-8", errors="replace") as fh:
            ref = fh.read().strip()
    except OSError:
        return ""
    if ref.startswith("ref: refs/heads/"):
        return ref.split("refs/heads/", 1)[1]
    return ref[:7]
