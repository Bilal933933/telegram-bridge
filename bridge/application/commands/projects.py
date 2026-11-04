"""قائمة مشاريع المحرّك النشط (OpenCode أو Qoder أو أي محرّك آخر)."""
from bridge.presentation import screens


def run(ctx, chat_id, arg=""):
    engine = ctx.projects.active(chat_id)
    items = ctx.projects.list_projects(chat_id, 12)
    if not items:
        ctx.messenger.send(chat_id,
                           f"لا توجد مشاريع مسجّلة في {screens.engine_label(engine)} بعد.\n"
                           "أرسل /cd لتحديد مجلد العمل.")
        return
    rows = []
    for p in items[:10]:
        key = ctx.callbacks.put({"dir": p["dir"], "pid": p.get("id")})
        rows.append([{"text": f"📁 {screens.folder(p['dir'])} · {screens.ago(p['active'])}",
                      "callback_data": f"pr:{key}"}])
    ctx.messenger.send(chat_id, screens.projects_text(items, engine),
                       ctx.keyboards.kb(rows))
