"""فتح جلسة: OpenCode بالمعرّف، أو Qoder برقم المحادثة."""
from bridge.application.commands import session_view, sessions


def run(ctx, chat_id, arg=""):
    arg = (arg or "").strip()
    if not arg:
        ctx.messenger.send(chat_id, "استخدم: /open <رقم>")
        return
    st = ctx.state.get(chat_id)
    if st["src"] == "opencode":
        items = ctx.engines.get("opencode").sessions_in(st["workdir"], 20)
        match = [it for it in items
                 if it["id"].startswith(arg) or it["id"].endswith(arg)]
        if not match:
            ctx.messenger.send(chat_id, "لم أجد الجلسة. أرسل /sessions.")
            return
        session_view.run(ctx, chat_id,
                         ctx.callbacks.put({"sid": match[0]["id"], "dir": st["workdir"]}))
        return
    sessions.open_index(ctx, chat_id, arg)


def from_key(ctx, chat_id, key):
    """فتح جلسة من زر قائمة Qoder."""
    data = ctx.callbacks.get(key) or {}
    sid = data.get("sid")
    if not sid:
        ctx.messenger.send(chat_id, "انتهت صلاحية القائمة — أرسل /sessions.")
        return
    sessions.open_by_id(ctx, chat_id, sid)


def card(ctx, chat_id):
    """زر «بطاقة الجلسة» من القائمة الرئيسية."""
    st = ctx.state.get(chat_id)
    sid = st["oc_session"]
    if not sid:
        ctx.messenger.send(chat_id, "لا جلسة OpenCode بعد.\n"
                                    "🗂 المشاريع → اختر مشروعًا → 🆕 جلسة جديدة.",
                           ctx.keyboards.menu_kb())
        return
    session_view.run(ctx, chat_id,
                     ctx.callbacks.put({"sid": sid, "dir": st["workdir"]}), with_tail=False)
