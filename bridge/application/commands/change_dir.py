"""تغيير مساحة العمل، أو تصفّح المجلدات بالأزرار."""
import os
import pathlib


def run(ctx, chat_id, arg=""):
    arg = (arg or "").strip().strip('"')
    if not arg:
        browse(ctx, chat_id)
        return
    path = os.path.normpath(os.path.expanduser(arg))
    if not os.path.isdir(path):
        ctx.messenger.send(chat_id, f"❌ غير صالح:\n{path}")
        return
    st = ctx.state.get(chat_id)
    ctx.state.update(chat_id, workdir=path)
    if st["src"] == "qoder":
        ctx.state.update(chat_id, session_id="")
    ctx.messenger.send(chat_id, f"✅ مساحة العمل ({st['src']}): {path}")


def browse(ctx, chat_id, path=None):
    st = ctx.state.get(chat_id)
    path = path or st["workdir"]
    if not os.path.isdir(path):
        ctx.messenger.send(chat_id, f"❌ ليس مجلدًا صالحًا:\n{path}")
        return
    try:
        dirs = sorted(p.name for p in pathlib.Path(path).iterdir()
                      if p.is_dir() and not p.name.startswith("."))
    except OSError as exc:
        ctx.messenger.send(chat_id, f"❌ {exc}")
        return
    rows = [[{"text": f"📂 {d}", "callback_data": f"cd:{d}"}] for d in dirs[:12]]
    rows.append([{"text": "⬆️ أعلى", "callback_data": "cd:.."},
                 {"text": "✅ اعتماد", "callback_data": "cd:."}])
    ctx.messenger.send(chat_id, f"الحالي: {path}", ctx.keyboards.kb(rows))


def from_button(ctx, chat_id, target):
    st = ctx.state.get(chat_id)
    base = st["workdir"]
    if target == ".":
        ctx.state.update(chat_id, workdir=base)
        ctx.messenger.send(chat_id, f"✅ {base}")
        return
    new_path = os.path.normpath(os.path.join(base, target))
    if not os.path.isdir(new_path):
        ctx.messenger.send(chat_id, f"❌ {new_path}")
        return
    ctx.state.update(chat_id, workdir=new_path)
    browse(ctx, chat_id, new_path)
