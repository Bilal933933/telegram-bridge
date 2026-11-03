"""إنشاء جلسة: OpenCode تنشئ فورًا، وQoder تبدأ محادثة جديدة."""
from bridge.presentation import screens


def run(ctx, chat_id, arg=""):
    st = ctx.state.get(chat_id)
    if st["src"] == "opencode":
        try:
            sid = ctx.sessions.create(chat_id, st["workdir"], screens.folder(st["workdir"]))
        except Exception as exc:  # noqa: BLE001
            ctx.messenger.send(chat_id, f"⚠️ {exc}")
            return
        ctx.messenger.send(chat_id, f"✅ **جلسة جديدة** في {screens.folder(st['workdir'])}\n"
                                    f"🆔 `{sid}`{_topic(ctx, sid)}\n\nأرسل رسالتك الأولى.")
        ctx.screens.set(chat_id, "card")
        return
    ctx.state.update(chat_id, session_id="")
    ctx.messenger.send(chat_id, "🧹 محادثة Qoder جديدة.")


def from_project(ctx, chat_id, key):
    """زر «جلسة جديدة» داخل شاشة مشروع."""
    data = ctx.callbacks.get(key) or {}
    directory = data.get("dir") or ctx.state.get(chat_id)["workdir"]
    try:
        sid = ctx.sessions.create(chat_id, directory, screens.folder(directory))
    except Exception as exc:  # noqa: BLE001
        ctx.messenger.send(chat_id, f"⚠️ تعذر إنشاء الجلسة:\n{exc}")
        return
    ctx.messenger.send(chat_id, f"✅ **جلسة جديدة** في {screens.folder(directory)}\n"
                                f"🆔 `{sid}`{_topic(ctx, sid)}\n\nأرسل رسالتك الأولى.")
    ctx.screens.set(chat_id, "card")


def _topic(ctx, sid):
    link = ctx.topics.link(sid)
    return f"\n📂 الموضوع: {link}" if link else ""
