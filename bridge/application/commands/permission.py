"""الرد على طلب إذن أداة (OpenCode)."""


def run(ctx, chat_id, key, decision):
    entry = ctx.permissions.resolve(key)
    if not entry:
        ctx.messenger.send(chat_id, "انتهت صلاحية الطلب.")
        return
    sid, rid = entry
    try:
        ctx.engines.get("opencode").reply_permission(sid, rid, decision)
        ctx.messenger.send(chat_id, f"✅ تم: {decision}")
    except Exception as exc:  # noqa: BLE001
        ctx.messenger.send(chat_id, f"⚠️ {exc}")
