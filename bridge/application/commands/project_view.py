"""شاشة مشروع واحد: جلساته، وأزرار الفتح حسب قدرات المحرّك."""
from bridge.presentation import screens


def run(ctx, chat_id, key):
    data = ctx.callbacks.get(key) if key else None
    if not data:
        ctx.messenger.send(chat_id, "انتهت صلاحية الشاشة — أرسل /projects.")
        return
    directory = data["dir"]
    engine = ctx.projects.active(chat_id)
    items = ctx.projects.sessions(chat_id, directory, 20)
    rows = []
    for i, s in enumerate(items[:8], 1):
        rows.append([{"text": f"{i}. {s['title'][:30]} · {screens.ago(s.get('updated'))}",
                      "callback_data": _open_button(ctx, chat_id, directory, s)}])
    if ctx.projects.rich_cards(chat_id):
        pkey = ctx.callbacks.put({"dir": directory, "pid": data.get("pid")})
        rows.append([{"text": "🆕 جلسة جديدة", "callback_data": f"pn:{pkey}"}])
    rows.append([{"text": "⬅ المشاريع", "callback_data": "ph"}])
    ctx.messenger.send(chat_id, screens.project_text(directory, items, engine),
                       ctx.keyboards.kb(rows))


def _open_button(ctx, chat_id, directory, session):
    """بطاقة جلسة كاملة للمحرّكات الغنية، وفتح مباشر لغيرها."""
    sid = session["id"]
    if ctx.projects.rich_cards(chat_id):
        return f"ps:{ctx.callbacks.put({'sid': sid, 'dir': directory})}"
    engine = ctx.projects.active(chat_id)
    return f"open:{ctx.callbacks.put({'sid': sid, 'dir': directory, 'engine': engine})}"
