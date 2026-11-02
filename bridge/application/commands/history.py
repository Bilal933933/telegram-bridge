"""عرض محادثة المحرّك النشط."""
from bridge.presentation import screens


def run(ctx, chat_id, arg=""):
    limit = int(arg) if str(arg).isdigit() else 40
    st = ctx.state.get(chat_id)
    if st["src"] == "opencode":
        return all_messages(ctx, chat_id, limit)

    sid = st["session_id"]
    if not sid:
        ctx.messenger.send(chat_id, "لا جلسة Qoder مفتوحة — أرسل /sessions.")
        return
    text = screens.history_entries(ctx.engines.get("qoder").history(sid, limit))
    ctx.messenger.send(chat_id, text or "لا رسائل في هذه الجلسة بعد.")


def all_messages(ctx, chat_id, limit=40):
    """كل رسائل جلسة OpenCode الحالية."""
    st = ctx.state.get(chat_id)
    sid = st["oc_session"]
    if not sid:
        ctx.messenger.send(chat_id, "لا توجد جلسة مفتوحة — أرسل /projects أو /sessions.")
        return
    limit = limit or 100
    try:
        context = ctx.sessions.context(sid)
        text = screens.history(context, limit)
    except Exception as exc:  # noqa: BLE001
        ctx.messenger.send(chat_id, f"⚠️ {exc}")
        return
    total = len(context)
    head = f"📜 **آخر {min(limit, total)} من {total} رسالة**\n\n"
    ctx.messenger.send(chat_id, head + (text or "(الجلسة فارغة)"))
