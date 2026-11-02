"""شاشة مشروع واحد: جلساته + إنشاء جلسة جديدة."""
from bridge.presentation import screens


def run(ctx, chat_id, key):
    data = ctx.callbacks.get(key) if key else None
    if not data:
        ctx.messenger.send(chat_id, "انتهت صلاحية الشاشة — أرسل /projects.")
        return
    directory = data["dir"]
    sessions = ctx.projects.sessions(directory, 20)
    pkey = ctx.callbacks.put({"dir": directory, "pid": data.get("pid")})
    rows = []
    for i, s in enumerate(sessions[:8], 1):
        skey = ctx.callbacks.put({"sid": s["id"], "dir": directory, "pkey": pkey})
        rows.append([{"text": f"{i}. {s['title'][:30]} · {screens.ago(s['updated'])}",
                      "callback_data": f"ps:{skey}"}])
    rows.append([{"text": "🆕 جلسة جديدة", "callback_data": f"pn:{pkey}"}])
    rows.append([{"text": "⬅ المشاريع", "callback_data": "ph"}])
    ctx.messenger.send(chat_id, screens.project_text(directory, sessions),
                       ctx.keyboards.kb(rows))
