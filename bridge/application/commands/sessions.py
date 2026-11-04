"""قائمة جلسات المحرّك النشط (OpenCode أو Qoder أو أي محرّك آخر)."""
from bridge.presentation import screens


def run(ctx, chat_id, arg=""):
    st = ctx.state.get(chat_id)
    directory = st["workdir"]
    items = ctx.projects.sessions(chat_id, directory, 20)
    if not items:
        ctx.messenger.send(chat_id,
                           f"لا توجد جلسات في {screens.folder(directory)} "
                           f"({screens.engine_label(st['src'])}).")
        return
    rows = []
    for i, s in enumerate(items[:10], 1):
        rows.append([{"text": f"{i}. {s['title'][:34]}",
                      "callback_data": _open_button(ctx, chat_id, directory, s)}])
    ctx.messenger.send(chat_id,
                       f"💬 **جلسات {screens.folder(directory)}** · "
                       f"{screens.engine_label(st['src'])} — {len(items)}",
                       ctx.keyboards.kb(rows))


def _open_button(ctx, chat_id, directory, session):
    """بطاقة جلسة كاملة للمحرّكات الغنية، وفتح مباشر لغيرها."""
    sid = session["id"]
    if ctx.projects.rich_cards(chat_id):
        return f"ps:{ctx.callbacks.put({'sid': sid, 'dir': directory})}"
    engine = ctx.projects.active(chat_id)
    return f"open:{ctx.callbacks.put({'sid': sid, 'dir': directory, 'engine': engine})}"


def open_index(ctx, chat_id, index):
    """فتح جلسة Qoder برقمها كما في القائمة."""
    st = ctx.state.get(chat_id)
    items = ctx.engines.get("qoder").list_sessions(st["workdir"])
    match = [it for it in items if str(it["index"]) == str(index)]
    if not match:
        ctx.messenger.send(chat_id, "لم أجد المحادثة. أرسل /sessions.")
        return
    open_by_id(ctx, chat_id, match[0]["id"])


def open_by_id(ctx, chat_id, sid, directory=None):
    changes = {"src": "qoder", "session_id": sid}
    if directory:
        changes["workdir"] = directory
        changes["project"] = directory
    ctx.state.update(chat_id, **changes)
    ctx.messenger.send(chat_id, screens.qoder_card(ctx.state.get(chat_id), sid))
    text = screens.history_entries(ctx.engines.get("qoder").history(sid, 10))
    ctx.messenger.send(chat_id, ("📜 **آخر الرسائل**\n\n" + text) if text else
                       "📜 لا رسائل في هذه الجلسة بعد.")
