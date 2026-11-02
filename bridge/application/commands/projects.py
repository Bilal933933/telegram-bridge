"""قائمة مشاريع OpenCode."""
from bridge.presentation import screens


def run(ctx, chat_id, arg=""):
    st = ctx.state.get(chat_id)
    note = ("" if st["src"] == "opencode" else
            "🔌 المحرّك الحالي Qoder — فتح جلسة سيبدّل تلقائيًا إلى OpenCode.\n\n")
    items = ctx.projects.list_projects(12)
    if not items:
        ctx.messenger.send(chat_id, "لا توجد مشاريع مسجّلة في OpenCode بعد.\nأرسل /cd لإضافة مسار.")
        return
    rows = []
    for p in items[:10]:
        key = ctx.callbacks.put({"dir": p["dir"], "pid": p["id"]})
        rows.append([{"text": f"📁 {screens.folder(p['dir'])} · {screens.ago(p['active'])}",
                      "callback_data": f"pr:{key}"}])
    ctx.messenger.send(chat_id, note + screens.projects_text(items), ctx.keyboards.kb(rows))
