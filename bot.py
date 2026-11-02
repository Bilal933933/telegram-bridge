#!/usr/bin/env python3
"""بوت تيليجرام — واجهة موحّدة لمحرّكي Qoder و OpenCode."""
import functools
import os
import pathlib
import threading
import time
import urllib.error

import config
import formatting
import state
import telegram as tg_mod
from backends import opencode as oc
from backends import qoder as qd
from bridge.shared.error_boundary import ErrorBoundary
from bridge.shared.logging_setup import configure_logging, get_logger
from engine import actions as ui
from engine import lifecycle, registry, screens

configure_logging()
logger = get_logger("bot")

TG = tg_mod.Telegram(config.TOKEN)
kb = tg_mod.kb

LAST_QODER = {}
LAST_OC = {}
PERMS = {}
PERM_SEQ = [0]
BUSY = {}
LOCK = threading.Lock()

HELP = (
    "👋 **كيف يعمل**\n\n"
    "1️⃣ اضغط **🗂 المشاريع** واختر مجلدًا\n"
    "2️⃣ اضغط جلسة (أو 🆕 جلسة جديدة)\n"
    "3️⃣ اكتب رسالتك — الوكيل ينفّذها على جهازك ويعيد الرد\n\n"
    "كل رسالة تذهب إلى نفس الجلسة حتى تفتح غيرها.\n"
    "الأوامر: /projects · /sessions · /new · /history · /agent · /model · /stop · /status"
)


def send(chat_id, text, keyboard=None):
    parts = [formatting.to_html(c) for c in formatting.chunks(text or "…")]
    for idx, chunk in enumerate(parts):
        TG.send(chat_id, chunk, kb=keyboard if idx == len(parts) - 1 else None)


ui.bind(send, kb)


def notify_error(chat_id, text):
    """إشعار الخطأ للمالك فقط."""
    if chat_id == config.OWNER:
        send(chat_id, text)


BOUNDARY = ErrorBoundary(notify_error)


def spawn(chat_id, target, *args):
    """يشغّل target في خيط خلفي داخل ErrorBoundary فلا يموت الخيط بصمت."""
    threading.Thread(
        target=BOUNDARY.run,
        args=(chat_id, functools.partial(target, *args)),
        daemon=True,
    ).start()


def callback_chat_id(cq):
    return (cq.get("message") or {}).get("chat", {}).get("id")


def typing(chat_id, stop_event):
    while not stop_event.wait(4.5):
        TG.action(chat_id, "typing")


def is_busy(chat_id):
    return BUSY.get(chat_id, False)


def set_busy(chat_id, value):
    with LOCK:
        BUSY[chat_id] = value


def menu_kb():
    return kb([
        [{"text": "🗂 المشاريع", "callback_data": "ph"},
         {"text": "💬 جلسات المشروع", "callback_data": "sessions"}],
        [{"text": "🆕 جلسة جديدة", "callback_data": "new"},
         {"text": "🔌 المحرّك", "callback_data": "src"}],
        [{"text": "📊 بطاقة الجلسة", "callback_data": "card"},
         {"text": "🤖 الوكيل", "callback_data": "ag"}],
        [{"text": "ℹ️ الحالة", "callback_data": "status"},
         {"text": "❓ مساعدة", "callback_data": "help"}],
    ])


def engines_text(chat_id):
    """سطران: آخر جلسة في كل محرّك، والنشط معلَّم."""
    data = state.summary(chat_id)
    lines = []
    for engine, label in (("opencode", "OpenCode"), ("qoder", "Qoder")):
        item = data[engine]
        sid = item.get("oc_session") if engine == "opencode" else item.get("session_id")
        mark = "▶️" if data["active"] == engine else "▫️"
        bits = [f"{mark} **{label}**", f"📁 {screens.folder(item['workdir'])}"]
        bits.append(f"💬 {sid[-8:] if sid else '—'}")
        if item.get("model"):
            bits.append(f"🧠 {item['model']}")
        lines.append(" · ".join(bits))
    return "\n".join(lines)


# ---------- عرض ----------

def show_sessions(chat_id):
    st = state.get(chat_id)
    if st["src"] == "opencode":
        ui.show_project(chat_id, registry.put({"dir": st["workdir"]}))
        return

    items = qd.list_sessions(st["workdir"])
    if not items:
        send(chat_id, f"لا توجد محادثات في:\n{st['workdir']}")
        return
    LAST_QODER[chat_id] = {str(it["index"]): it["id"] for it in items}
    rows = [[{"text": f"{it['index']}. {it['title'][:34]}", "callback_data": f"open:{it['index']}"}]
            for it in items[:10]]
    send(chat_id, f"محادثات Qoder ({len(items)}):", kb(rows))


def show_dirs(chat_id, path=None):
    st = state.get(chat_id)
    path = path or st["workdir"]
    if not os.path.isdir(path):
        send(chat_id, f"❌ ليس مجلدًا صالحًا:\n{path}")
        return
    try:
        dirs = sorted(p.name for p in pathlib.Path(path).iterdir()
                      if p.is_dir() and not p.name.startswith("."))
    except OSError as exc:
        send(chat_id, f"❌ {exc}")
        return
    rows = [[{"text": f"📂 {d}", "callback_data": f"cd:{d}"}] for d in dirs[:12]]
    rows.append([{"text": "⬆️ أعلى", "callback_data": "cd:.."},
                 {"text": "✅ اعتماد", "callback_data": "cd:."}])
    send(chat_id, f"الحالي: {path}", kb(rows))


def show_models(chat_id):
    st = state.get(chat_id)
    models = qd.list_models(st["workdir"])
    if not models:
        send(chat_id, "تعذر جلب النماذج.")
        return
    rows = [[{"text": m, "callback_data": f"model:{m}"}] for m in models[:10]]
    send(chat_id, f"النموذج: {st['model'] or '(افتراضي)'}", kb(rows))


def show_history(chat_id, limit=40):
    st = state.get(chat_id)
    if st["src"] == "opencode":
        ui.show_history(chat_id, limit)
        return
    sid = st["session_id"]
    if not sid:
        send(chat_id, "لا جلسة Qoder مفتوحة — أرسل /sessions.")
        return
    text = screens.history_entries(qd.read_messages(sid, limit))
    send(chat_id, text or "لا رسائل في هذه الجلسة بعد.")


# ---------- تشغيل ----------

def ask_qoder(chat_id, text):
    st = state.get(chat_id)
    streamer = tg_mod.Streamer(TG, chat_id)
    stop_event = threading.Event()
    spawn(None, typing, chat_id, stop_event)
    set_busy(chat_id, True)
    try:
        body, sid, error = qd.stream(
            text, st["session_id"], st["workdir"], st["model"],
            on_delta=lambda t: streamer.update(t),
            on_tool=lambda n, d: streamer.tool(n, d),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("qoder stream failed chat=%s", chat_id)
        body, sid, error = "", None, str(exc)
    finally:
        stop_event.set()
        set_busy(chat_id, False)
    if sid and sid != st["session_id"]:
        state.update(chat_id, session_id=sid)
    qd.log_turn(sid or st["session_id"], text, body, error)
    streamer.finish(body or (f"⚠️ {error}" if error else "(لا مخرجات)"))


def ask_opencode(chat_id, text):
    st = state.get(chat_id)
    sid = st["oc_session"]
    if not sid:
        try:
            sid = oc.create("تيليجرام", st["workdir"])
        except Exception as exc:  # noqa: BLE001
            logger.exception("opencode create session failed chat=%s", chat_id)
            send(chat_id, f"⚠️ تعذر إنشاء جلسة:\n{exc}")
            return
        state.update(chat_id, oc_session=sid)
    if oc.is_active(sid):
        send(chat_id, "⏳ **هذه الجلسة مشغولة** بردّ جارٍ.\n"
                      "افتح جلسة أخرى أو أنشئ جديدة:",
             kb([[{"text": "🆕 جلسة جديدة", "callback_data": "new"}],
                 [{"text": "💬 جلسات المشروع", "callback_data": "sessions"}]]))
        return

    streamer = tg_mod.Streamer(TG, chat_id)
    stop_event = threading.Event()
    spawn(None, typing, chat_id, stop_event)
    set_busy(chat_id, True)

    def on_perm(req):
        PERM_SEQ[0] += 1
        key = f"p{PERM_SEQ[0]}"
        PERMS[key] = (sid, req.get("id"))
        action = req.get("action") or "أداة"
        rows = [[{"text": "✅ مرة واحدة", "callback_data": f"perm:{key}:once"},
                 {"text": "♾️ دائمًا", "callback_data": f"perm:{key}:always"}],
                [{"text": "⛔ رفض", "callback_data": f"perm:{key}:reject"}]]
        send(chat_id, f"🔐 طلب إذن: {action}", kb(rows))

    try:
        body, error = oc.stream(
            sid, text,
            on_delta=lambda t: streamer.update(t),
            on_tool=lambda n, d: streamer.tool(n, d),
            on_permission=on_perm,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("opencode stream failed chat=%s", chat_id)
        body, error = "", str(exc)
    finally:
        stop_event.set()
        set_busy(chat_id, False)
    streamer.finish(body or (f"⚠️ {error}" if error else "(لا مخرجات)"))


# ---------- الأوامر ----------

def handle(chat_id, text):
    text = text.strip()
    low = text.lower()
    st = state.get(chat_id)

    if low in ("/start", "/help", "/menu"):
        send(chat_id, HELP, menu_kb())
        return

    if low == "/src" or low.startswith("/src "):
        arg = text[4:].strip().lower()
        if arg in ("qoder", "opencode"):
            state.switch(chat_id, arg)
            send(chat_id, f"✅ المحرّك: **{arg}**\n\n{engines_text(chat_id)}", menu_kb())
            return
        rows = [[{"text": "Qoder CLI", "callback_data": "src:qoder"}],
                [{"text": "OpenCode", "callback_data": "src:opencode"}]]
        send(chat_id, (f"🔌 **المحرّك الحالي:** {st['src']}\n\n"
                       f"{engines_text(chat_id)}\n\n"
                       "• OpenCode — مشاريع وجلسات وبطاقة حالة\n"
                       "• Qoder — CLI مباشر بلا مشاريع\n"
                       "كل محرّك يحتفظ بمجلده وجلسته."), kb(rows))
        return

    if low == "/new":
        if st["src"] == "opencode":
            try:
                sid = lifecycle.create(chat_id, st["workdir"], screens.folder(st["workdir"]))
            except Exception as exc:  # noqa: BLE001
                send(chat_id, f"⚠️ {exc}")
                return
            ui.show_session(chat_id, registry.put({"sid": sid, "dir": st["workdir"]}))
        else:
            state.update(chat_id, session_id="")
            send(chat_id, "🧹 محادثة Qoder جديدة.")
        return

    if low == "/projects":
        ui.show_projects(chat_id)
        return

    if low == "/status":
        busy = "تعمل" if is_busy(chat_id) else "لا مهمة جارية"
        rows = [[{"text": "📊 بطاقة الجلسة", "callback_data": "card"},
                 {"text": "🗂 المشاريع", "callback_data": "ph"}]]
        send(chat_id, f"🔌 **المحرّك النشط:** {st['src']} · {busy}\n\n"
                      f"{engines_text(chat_id)}", kb(rows))
        return

    if low == "/stop":
        if st["src"] == "opencode" and st["oc_session"]:
            ok = oc.interrupt(st["oc_session"])
            send(chat_id, "🛑 أُرسل طلب الإيقاف." if ok else "لا توجد مهمة.")
        else:
            ok = qd.stop()
            send(chat_id, "🛑 أُوقفت مهمة Qoder." if ok else "لا توجد مهمة.")
        return

    if low == "/sessions":
        show_sessions(chat_id)
        return

    if low.startswith("/history"):
        arg = text[8:].strip()
        limit = int(arg) if arg.isdigit() else 40
        show_history(chat_id, limit)
        return

    if low.startswith("/open"):
        arg = text[5:].strip()
        if not arg:
            send(chat_id, "استخدم: /open <رقم>")
            return
        if st["src"] == "opencode":
            try:
                items = oc.sessions_in(st["workdir"], 20)
            except Exception:  # noqa: BLE001
                items = []
            match = [it for it in items
                     if it["id"].startswith(arg) or it["id"].endswith(arg)]
            if not match:
                send(chat_id, "لم أجد الجلسة. أرسل /sessions.")
                return
            ui.show_session(chat_id, registry.put({"sid": match[0]["id"],
                                                   "dir": st["workdir"]}))
            return
        sid = LAST_QODER.get(chat_id, {}).get(arg)
        if not sid:
            items = qd.list_sessions(st["workdir"])
            match = [it for it in items if str(it["index"]) == arg or it["id"].startswith(arg)]
            sid = match[0]["id"] if match else None
        if not sid:
            send(chat_id, "لم أجد المحادثة. أرسل /sessions.")
            return
        state.update(chat_id, session_id=sid)
        send(chat_id, f"✅ فُتحت ({sid[:8]}).")
        return

    if low.startswith("/cd"):
        arg = text[3:].strip().strip('"')
        if not arg:
            show_dirs(chat_id)
            return
        path = os.path.normpath(os.path.expanduser(arg))
        if not os.path.isdir(path):
            send(chat_id, f"❌ غير صالح:\n{path}")
            return
        state.update(chat_id, workdir=path)
        if st["src"] == "qoder":
            state.update(chat_id, session_id="")
        send(chat_id, f"✅ مساحة العمل ({st['src']}): {path}")
        return

    if low.startswith("/model"):
        arg = text[6:].strip()
        if st["src"] == "opencode":
            ui.show_models(chat_id, arg)
            return
        if not arg:
            show_models(chat_id)
            return
        models = qd.list_models(st["workdir"])
        match = [m for m in models if m.lower() == arg.lower()]
        if not match:
            send(chat_id, "❌ غير متاح:\n" + "\n".join(models))
            return
        state.update(chat_id, model=match[0])
        send(chat_id, f"✅ النموذج: {match[0]}")
        return

    if low == "/agent":
        if st["src"] != "opencode":
            send(chat_id, "تبديل الوكيل متاح في OpenCode فقط.")
            return
        ui.show_agents(chat_id)
        return

    if is_busy(chat_id):
        send(chat_id, "⏳ فيه مهمة شغالة. أرسل /stop.")
        return

    if st["src"] == "opencode":
        spawn(chat_id, ask_opencode, chat_id, text)
    else:
        spawn(chat_id, ask_qoder, chat_id, text)


def handle_callback(cq):
    chat_id = callback_chat_id(cq)
    data = cq.get("data") or ""
    TG.answer(cq.get("id"))
    if chat_id != config.OWNER:
        return
    st = state.get(chat_id)

    if ui.handle(chat_id, data):
        return

    if data.startswith("src:"):
        src = data.split(":", 1)[1]
        state.update(chat_id, src=src)
        send(chat_id, f"✅ المحرّك: **{src}**\n\n{engines_text(chat_id)}", menu_kb())

    elif data == "sessions":
        show_sessions(chat_id)

    elif data == "card":
        oc_ns = state.ns(chat_id, "opencode")
        sid = oc_ns.get("oc_session")
        if sid:
            ui.show_session(chat_id, registry.put({"sid": sid, "dir": oc_ns["workdir"]}))
        else:
            send(chat_id, "لا جلسة OpenCode بعد.\n"
                          "🗂 المشاريع → اختر مشروعًا → 🆕 جلسة جديدة.", menu_kb())

    elif data == "new":
        handle(chat_id, "/new")

    elif data == "status":
        handle(chat_id, "/status")

    elif data == "help":
        send(chat_id, HELP, menu_kb())

    elif data.startswith("open:"):
        idx = data.split(":", 1)[1]
        sid = LAST_QODER.get(chat_id, {}).get(idx)
        if sid:
            state.update(chat_id, session_id=sid)
            send(chat_id, screens.qoder_card(state.get(chat_id), sid))
            text = screens.history_entries(qd.read_messages(sid, 10))
            send(chat_id, ("📜 **آخر الرسائل**\n\n" + text) if text else
                 "📜 لا رسائل في هذه الجلسة بعد.")

    elif data.startswith("ocopen:"):
        idx = data.split(":", 1)[1]
        sid = LAST_OC.get(chat_id, {}).get(idx)
        if sid:
            ui.show_session(chat_id, registry.put({"sid": sid, "dir": st["workdir"]}))

    elif data.startswith("cd:"):
        target = data.split(":", 1)[1]
        base = st["workdir"]
        if target == ".":
            state.update(chat_id, workdir=base)
            send(chat_id, f"✅ {base}")
            return
        new_path = os.path.normpath(os.path.join(base, target))
        if not os.path.isdir(new_path):
            send(chat_id, f"❌ {new_path}")
            return
        state.update(chat_id, workdir=new_path)
        show_dirs(chat_id, new_path)

    elif data.startswith("model:"):
        name = data.split(":", 1)[1]
        state.update(chat_id, model=name)
        send(chat_id, f"✅ النموذج: {name}")

    elif data.startswith("perm:"):
        _, key, decision = data.split(":", 2)
        entry = PERMS.pop(key, None)
        if not entry:
            send(chat_id, "انتهت صلاحية الطلب.")
            return
        sid, rid = entry
        try:
            oc.reply_permission(sid, rid, decision)
            send(chat_id, f"✅ تم: {decision}")
        except Exception as exc:  # noqa: BLE001
            send(chat_id, f"⚠️ {exc}")


def main():
    if not config.TOKEN or not config.OWNER:
        logger.error("BOT_TOKEN أو ALLOWED_ID مفقود في .env")
        return 1
    logger.info("بدء البوت | owner=%s | dir=%s", config.OWNER, config.DEFAULT_DIR)
    offset = 0
    while True:
        try:
            res = TG.call("getUpdates", offset=offset, timeout=30,
                          allowed_updates='["message","callback_query"]')
            for upd in res.get("result", []):
                offset = upd["update_id"] + 1
                if "callback_query" in upd:
                    cq = upd["callback_query"]
                    spawn(callback_chat_id(cq), handle_callback, cq)
                    continue
                msg = upd.get("message") or {}
                chat_id = (msg.get("chat") or {}).get("id")
                text = msg.get("text") or ""
                if chat_id != config.OWNER or not text:
                    continue
                spawn(chat_id, handle, chat_id, text)
        except urllib.error.HTTPError as exc:
            logger.warning("getUpdates HTTP %s", exc.code)
            time.sleep(5)
        except Exception:  # noqa: BLE001
            logger.exception("loop error")
            time.sleep(5)


if __name__ == "__main__":
    raise SystemExit(main())
