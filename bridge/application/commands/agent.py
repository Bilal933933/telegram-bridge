"""اختيار الوكيل (OpenCode فقط)."""


def run(ctx, chat_id, arg=""):
    st = ctx.state.get(chat_id)
    if st["src"] != "opencode":
        ctx.messenger.send(chat_id, "تبديل الوكيل متاح في OpenCode فقط.")
        return
    show(ctx, chat_id)


def show(ctx, chat_id):
    st = ctx.state.get(chat_id)
    sid = st["oc_session"]
    if not sid:
        ctx.messenger.send(chat_id, "افتح جلسة أولًا (/sessions).")
        return
    try:
        items = ctx.engines.get("opencode").list_agents(st["workdir"])
    except Exception as exc:  # noqa: BLE001
        ctx.messenger.send(chat_id, f"⚠️ {exc}")
        return
    rows = []
    for a in items:
        key = ctx.callbacks.put({"sid": sid, "agent": a["id"]})
        rows.append([{"text": a["name"], "callback_data": f"agx:{key}"}])
    ctx.messenger.send(chat_id, "🤖 **الوكيل** — اختر (مثل Tab في البرنامج):",
                       ctx.keyboards.kb(rows))


def set_agent(ctx, chat_id, key):
    data = ctx.callbacks.get(key)
    if not data:
        ctx.messenger.send(chat_id, "انتهت صلاحية الاختيار — أرسل /agent.")
        return
    try:
        ctx.sessions.switch_agent(data["sid"], data["agent"])
    except Exception as exc:  # noqa: BLE001
        ctx.messenger.send(chat_id, f"⚠️ {exc}")
        return
    ctx.messenger.send(chat_id, f"✅ الوكيل: **{data['agent']}**")
