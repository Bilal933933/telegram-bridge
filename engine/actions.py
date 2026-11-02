"""أوامر وأزرار الشاشات: مشاريع ← مشروع ← جلسة، ووكلاء/نماذج/تاريخ."""
from bridge.container import callbacks, state
from bridge.infrastructure.engines.registry import get as get_engine

from . import lifecycle, projects, screens


def _engine():
    return get_engine("opencode")

_send = None
_kb = None


def bind(send, kb):
    """يربط وحدة الشاشات بدوال الإرسال في البوت (تفادي الاستيراد الدائري)."""
    global _send, _kb
    _send, _kb = send, kb


def _out(chat_id, text, rows=None):
    _send(chat_id, text, _kb(rows) if rows else None)


# ---------- المشاريع ----------

def show_projects(chat_id):
    st = state.get(chat_id)
    note = ("" if st["src"] == "opencode" else
            "🔌 المحرّك الحالي Qoder — فتح جلسة سيبدّل تلقائيًا إلى OpenCode.\n\n")
    items = projects.list_projects(12)
    if not items:
        _out(chat_id, "لا توجد مشاريع مسجّلة في OpenCode بعد.\nأرسل /cd لإضافة مسار.")
        return
    rows = []
    for p in items[:10]:
        key = callbacks.put({"dir": p["dir"], "pid": p["id"]})
        rows.append([{"text": f"📁 {screens.folder(p['dir'])} · {screens.ago(p['active'])}",
                      "callback_data": f"pr:{key}"}])
    _out(chat_id, note + screens.projects_text(items), rows)


def show_project(chat_id, key):
    data = callbacks.get(key)
    if not data:
        _out(chat_id, "انتهت صلاحية الشاشة — أرسل /projects.")
        return
    directory = data["dir"]
    sessions = projects.sessions(directory, 20)
    pkey = callbacks.put({"dir": directory, "pid": data.get("pid")})
    rows = []
    for i, s in enumerate(sessions[:8], 1):
        skey = callbacks.put({"sid": s["id"], "dir": directory, "pkey": pkey})
        rows.append([{"text": f"{i}. {s['title'][:30]} · {screens.ago(s['updated'])}",
                      "callback_data": f"ps:{skey}"}])
    rows.append([{"text": "🆕 جلسة جديدة", "callback_data": f"pn:{pkey}"}])
    rows.append([{"text": "⬅ المشاريع", "callback_data": "ph"}])
    _out(chat_id, screens.project_text(directory, sessions), rows)


def new_session(chat_id, pkey):
    data = callbacks.get(pkey) or {}
    directory = data.get("dir") or state.get(chat_id)["workdir"]
    try:
        sid = lifecycle.create(chat_id, directory, screens.folder(directory))
    except Exception as exc:  # noqa: BLE001
        _out(chat_id, f"⚠️ تعذر إنشاء الجلسة:\n{exc}")
        return
    _out(chat_id, f"✅ **جلسة جديدة** في {screens.folder(directory)}\n"
                  f"🆔 `{sid}`\n\nأرسل رسالتك الأولى.")


# ---------- الجلسة ----------

def show_session(chat_id, key):
    data = callbacks.get(key)
    if not data:
        _out(chat_id, "انتهت صلاحية الشاشة — أرسل /sessions أو /projects.")
        return
    sid = data["sid"]
    try:
        info = lifecycle.open(chat_id, sid, data.get("dir"))
    except Exception as exc:  # noqa: BLE001
        _out(chat_id, f"⚠️ تعذر فتح الجلسة:\n{exc}")
        return
    busy = lifecycle.busy(sid)
    try:
        pending = len(_engine().permissions(sid))
    except Exception:  # noqa: BLE001
        pending = 0
    skey = callbacks.put({"sid": sid, "dir": data.get("dir"), "pkey": data.get("pkey")})
    rows = [
        [{"text": "📜 كل الرسائل", "callback_data": "hist"},
         {"text": "🔄 تحديث", "callback_data": f"ps:{skey}"}],
        [{"text": "🤖 الوكيل", "callback_data": "ag"},
         {"text": "🧠 النموذج", "callback_data": "md"}],
    ]
    if data.get("pkey"):
        rows.append([{"text": "⬅ المشروع", "callback_data": f"pb:{data['pkey']}"}])
    _out(chat_id, screens.session_text(info, busy, pending), rows)
    try:
        ctx = _engine().context(sid)
        tail = screens.tail(ctx, 10)
        total = screens.talk_count(ctx)
    except Exception:  # noqa: BLE001
        tail, total = "", 0
    if tail:
        head = (f"📜 **آخر الرسائل** ({min(total, 10)} من {total})"
                if total else "📜 **آخر النشاط**")
        _out(chat_id, f"{head}\n\n{tail}")
    else:
        _out(chat_id, "📜 الجلسة فارغة — أرسل رسالتك الأولى.")


def show_history(chat_id, limit=40):
    st = state.get(chat_id)
    sid = st["oc_session"]
    if not sid:
        _out(chat_id, "لا توجد جلسة مفتوحة — أرسل /projects أو /sessions.")
        return
    limit = limit or 100
    try:
        ctx = _engine().context(sid)
        text = screens.history(ctx, limit)
    except Exception as exc:  # noqa: BLE001
        _out(chat_id, f"⚠️ {exc}")
        return
    total = len(ctx)
    head = f"📜 **آخر {min(limit, total)} من {total} رسالة**\n\n"
    _out(chat_id, head + (text or "(الجلسة فارغة)"))


# ---------- الوكيل والنموذج ----------

def show_agents(chat_id):
    st = state.get(chat_id)
    sid = st["oc_session"]
    if not sid:
        _out(chat_id, "افتح جلسة أولًا (/sessions).")
        return
    try:
        items = _engine().list_agents(st["workdir"])
    except Exception as exc:  # noqa: BLE001
        _out(chat_id, f"⚠️ {exc}")
        return
    rows = []
    for a in items:
        key = callbacks.put({"sid": sid, "agent": a["id"]})
        rows.append([{"text": a["name"], "callback_data": f"agx:{key}"}])
    _out(chat_id, "🤖 **الوكيل** — اختر (مثل Tab في البرنامج):", rows)


def set_agent(chat_id, key):
    data = callbacks.get(key)
    if not data:
        _out(chat_id, "انتهت صلاحية الاختيار — أرسل /agent.")
        return
    try:
        lifecycle.switch_agent(data["sid"], data["agent"])
    except Exception as exc:  # noqa: BLE001
        _out(chat_id, f"⚠️ {exc}")
        return
    _out(chat_id, f"✅ الوكيل: **{data['agent']}**")


def show_models(chat_id, query=""):
    st = state.get(chat_id)
    sid = st["oc_session"]
    if not sid:
        _out(chat_id, "افتح جلسة أولًا (/sessions).")
        return
    try:
        items = _engine().list_model_details()
    except Exception as exc:  # noqa: BLE001
        _out(chat_id, f"⚠️ {exc}")
        return
    if query:
        items = [m for m in items if query.lower() in (m["id"] + m["name"]).lower()]
        if not items:
            _out(chat_id, f"لا نموذج يطابق «{query}».")
            return
    rows = []
    for m in items[:10]:
        key = callbacks.put({"sid": sid, "model": m["id"], "provider": m["provider"]})
        rows.append([{"text": m["name"][:40], "callback_data": f"mdx:{key}"}])
    _out(chat_id, f"🧠 **النموذج** — {len(items)} متاح:", rows)


def set_model(chat_id, key):
    data = callbacks.get(key)
    if not data:
        _out(chat_id, "انتهت صلاحية الاختيار — أرسل /model.")
        return
    try:
        lifecycle.switch_model(data["sid"], data["model"], data.get("provider"))
    except Exception as exc:  # noqa: BLE001
        _out(chat_id, f"⚠️ {exc}")
        return
    _out(chat_id, f"✅ النموذج: **{data['model']}**")


# ---------- التوجيه ----------

def handle(chat_id, data):
    """يعيد True إن كان الزر يخص شاشات المحرّك."""
    if data == "ph":
        show_projects(chat_id)
        return True
    if data == "hist":
        show_history(chat_id, None)
        return True
    if data == "ag":
        show_agents(chat_id)
        return True
    if data == "md":
        show_models(chat_id)
        return True
    for prefix, fn in (("pr:", show_project), ("ps:", show_session),
                       ("pn:", new_session), ("pb:", show_project),
                       ("agx:", set_agent), ("mdx:", set_model)):
        if data.startswith(prefix):
            fn(chat_id, data.split(":", 1)[1])
            return True
    return False
