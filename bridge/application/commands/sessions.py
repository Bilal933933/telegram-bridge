"""قائمة جلسات المحرّك النشط."""
from bridge.application.commands import project_view
from bridge.presentation import screens


def run(ctx, chat_id, arg=""):
    st = ctx.state.get(chat_id)
    if st["src"] == "opencode":
        project_view.run(ctx, chat_id, ctx.callbacks.put({"dir": st["workdir"]}))
        return

    items = ctx.engines.get("qoder").list_sessions(st["workdir"])
    if not items:
        ctx.messenger.send(chat_id, f"لا توجد محادثات في:\n{st['workdir']}")
        return
    rows = []
    for it in items[:10]:
        key = ctx.callbacks.put({"sid": it["id"], "engine": "qoder"})
        rows.append([{"text": f"{it['index']}. {it['title'][:34]}",
                      "callback_data": f"open:{key}"}])
    ctx.messenger.send(chat_id, f"محادثات Qoder ({len(items)}):", ctx.keyboards.kb(rows))


def open_index(ctx, chat_id, index):
    """فتح جلسة Qoder برقمها كما في القائمة."""
    st = ctx.state.get(chat_id)
    items = ctx.engines.get("qoder").list_sessions(st["workdir"])
    match = [it for it in items if str(it["index"]) == str(index)]
    if not match:
        ctx.messenger.send(chat_id, "لم أجد المحادثة. أرسل /sessions.")
        return
    open_by_id(ctx, chat_id, match[0]["id"])


def open_by_id(ctx, chat_id, sid):
    ctx.state.update(chat_id, session_id=sid)
    ctx.messenger.send(chat_id, screens.qoder_card(ctx.state.get(chat_id), sid))
    text = screens.history_entries(ctx.engines.get("qoder").history(sid, 10))
    ctx.messenger.send(chat_id, ("📜 **آخر الرسائل**\n\n" + text) if text else
                       "📜 لا رسائل في هذه الجلسة بعد.")
