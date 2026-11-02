"""تبديل المحرّك (Qoder / OpenCode) — لكل محرّك مجلده وجلسته."""
from bridge.presentation import screens

ENGINES = ("qoder", "opencode")


def run(ctx, chat_id, arg=""):
    arg = (arg or "").strip().lower()
    if arg in ENGINES:
        ctx.state.switch(chat_id, arg)
        summary = ctx.state.summary(chat_id)
        ctx.messenger.send(chat_id, f"✅ المحرّك: **{arg}**\n\n{screens.engines_text(summary)}",
                           ctx.keyboards.menu_kb())
        return
    st = ctx.state.get(chat_id)
    rows = [[{"text": "Qoder CLI", "callback_data": "src:qoder"}],
            [{"text": "OpenCode", "callback_data": "src:opencode"}]]
    ctx.messenger.send(chat_id, screens.engine_picker(st, ctx.state.summary(chat_id)),
                       ctx.keyboards.kb(rows))
