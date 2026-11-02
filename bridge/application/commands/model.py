"""اختيار النموذج: قائمة Qoder أو نماذج OpenCode."""
def run(ctx, chat_id, arg=""):
    st = ctx.state.get(chat_id)
    if st["src"] == "opencode":
        list_opencode(ctx, chat_id, arg)
        return
    if not arg:
        list_qoder(ctx, chat_id, st)
        return
    models = ctx.engines.get("qoder").list_models(st["workdir"])
    match = [m for m in models if m.lower() == arg.lower()]
    if not match:
        ctx.messenger.send(chat_id, "❌ غير متاح:\n" + "\n".join(models))
        return
    ctx.state.update(chat_id, model=match[0])
    ctx.messenger.send(chat_id, f"✅ النموذج: {match[0]}")


def list_qoder(ctx, chat_id, st):
    models = ctx.engines.get("qoder").list_models(st["workdir"])
    if not models:
        ctx.messenger.send(chat_id, "تعذر جلب النماذج.")
        return
    rows = [[{"text": m, "callback_data": f"model:{m}"}] for m in models[:10]]
    ctx.messenger.send(chat_id, f"النموذج: {st['model'] or '(افتراضي)'}",
                       ctx.keyboards.kb(rows))


def list_opencode(ctx, chat_id, query=""):
    st = ctx.state.get(chat_id)
    sid = st["oc_session"]
    if not sid:
        ctx.messenger.send(chat_id, "افتح جلسة أولًا (/sessions).")
        return
    try:
        items = ctx.engines.get("opencode").list_model_details()
    except Exception as exc:  # noqa: BLE001
        ctx.messenger.send(chat_id, f"⚠️ {exc}")
        return
    if query:
        items = [m for m in items if query.lower() in (m["id"] + m["name"]).lower()]
        if not items:
            ctx.messenger.send(chat_id, f"لا نموذج يطابق «{query}».")
            return
    rows = []
    for m in items[:10]:
        key = ctx.callbacks.put({"sid": sid, "model": m["id"], "provider": m["provider"]})
        rows.append([{"text": m["name"][:40], "callback_data": f"mdx:{key}"}])
    ctx.messenger.send(chat_id, f"🧠 **النموذج** — {len(items)} متاح:",
                       ctx.keyboards.kb(rows))


def set_qoder(ctx, chat_id, name):
    ctx.state.update(chat_id, model=name)
    ctx.messenger.send(chat_id, f"✅ النموذج: {name}")


def set_opencode(ctx, chat_id, key):
    data = ctx.callbacks.get(key)
    if not data:
        ctx.messenger.send(chat_id, "انتهت صلاحية الاختيار — أرسل /model.")
        return
    try:
        ctx.sessions.switch_model(data["sid"], data["model"], data.get("provider"))
    except Exception as exc:  # noqa: BLE001
        ctx.messenger.send(chat_id, f"⚠️ {exc}")
        return
    ctx.messenger.send(chat_id, f"✅ النموذج: **{data['model']}**")
