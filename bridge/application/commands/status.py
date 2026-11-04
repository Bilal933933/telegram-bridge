"""حالة المحرّك النشط والمهمة الجارية."""
from bridge.presentation import screens


def run(ctx, chat_id, arg=""):
    st = ctx.state.get(chat_id)
    busy = "تعمل" if ctx.busy.is_busy(chat_id) else "لا مهمة جارية"
    rows = [[{"text": "📊 بطاقة الجلسة", "callback_data": "card"},
             {"text": "🗂 المشاريع", "callback_data": "ph"}]]
    ctx.messenger.send(
        chat_id,
        f"🔌 **المحرّك النشط:** {screens.engine_label(st['src'])} · {busy}\n\n"
        f"{screens.active_engine_text(ctx.state.summary(chat_id), st['src'])}",
        ctx.keyboards.kb(rows),
    )
