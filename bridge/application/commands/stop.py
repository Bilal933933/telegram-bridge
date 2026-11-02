"""إيقاف المهمة الجارية في المحرّك النشط."""


def run(ctx, chat_id, arg=""):
    st = ctx.state.get(chat_id)
    if st["src"] == "opencode" and st["oc_session"]:
        ok = ctx.engines.get("opencode").interrupt(st["oc_session"])
        ctx.messenger.send(chat_id, "🛑 أُرسل طلب الإيقاف." if ok else "لا توجد مهمة.")
        return
    ok = ctx.engines.get("qoder").interrupt()
    ctx.messenger.send(chat_id, "🛑 أُوقفت مهمة Qoder." if ok else "لا توجد مهمة.")
