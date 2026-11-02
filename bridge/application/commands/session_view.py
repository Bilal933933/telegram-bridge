"""بطاقة جلسة OpenCode: الحالة، آخر الرسائل، وأزرار الوكيل/النموذج."""
from bridge.presentation import screens


def run(ctx, chat_id, key, with_tail=True):
    data = ctx.callbacks.get(key) if key else None
    if not data:
        ctx.messenger.send(chat_id, "انتهت صلاحية الشاشة — أرسل /sessions أو /projects.")
        return
    sid = data["sid"]
    try:
        info = ctx.sessions.open(chat_id, sid, data.get("dir"))
    except Exception as exc:  # noqa: BLE001
        ctx.messenger.send(chat_id, f"⚠️ تعذر فتح الجلسة:\n{exc}")
        return
    busy = ctx.sessions.busy(sid)
    try:
        pending = len(ctx.engines.get("opencode").permissions(sid))
    except Exception:  # noqa: BLE001
        pending = 0
    skey = ctx.callbacks.put({"sid": sid, "dir": data.get("dir"), "pkey": data.get("pkey")})
    rows = [
        [{"text": "📜 كل الرسائل", "callback_data": "hist"},
         {"text": "🔄 تحديث", "callback_data": f"ps:{skey}"}],
        [{"text": "🤖 الوكيل", "callback_data": "ag"},
         {"text": "🧠 النموذج", "callback_data": "md"}],
    ]
    if data.get("pkey"):
        rows.append([{"text": "⬅ المشروع", "callback_data": f"pb:{data['pkey']}"}])
    ctx.messenger.send(chat_id, screens.session_text(info, busy, pending),
                       ctx.keyboards.kb(rows))
    if not with_tail:
        return
    try:
        context = ctx.sessions.context(sid)
        tail = screens.tail(context, 10)
        total = screens.talk_count(context)
    except Exception:  # noqa: BLE001
        tail, total = "", 0
    if tail:
        head = (f"📜 **آخر الرسائل** ({min(total, 10)} من {total})"
                if total else "📜 **آخر النشاط**")
        ctx.messenger.send(chat_id, f"{head}\n\n{tail}")
    else:
        ctx.messenger.send(chat_id, "📜 الجلسة فارغة — أرسل رسالتك الأولى.")
