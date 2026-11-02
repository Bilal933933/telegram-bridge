"""دورة حياة الجلسة: فتح/إنشاء/حالة — كما يفعل البرنامج الحقيقي."""
import state
from backends import opencode as oc


def info(sid):
    return oc.session_info(sid)


def busy(sid):
    return oc.is_active(sid)


def open(chat_id, sid, directory=None):
    """فتح جلسة قائمة بنفس معرّفها الحقيقي (resume لا نسخة)."""
    data = oc.session_info(sid)
    directory = directory or (data.get("location") or {}).get("directory")
    state.update(chat_id, src="opencode", oc_session=sid,
                 workdir=directory or state.get(chat_id)["workdir"],
                 project=directory or "")
    return data


def create(chat_id, directory, title=None):
    sid = oc.create(title or "تيليجرام", directory)
    state.update(chat_id, src="opencode", oc_session=sid,
                 workdir=directory, project=directory)
    return sid


def switch_agent(sid, agent_id):
    return oc.set_agent(sid, agent_id)


def switch_model(sid, model_id, provider=""):
    return oc.set_model(sid, model_id, provider)


def history(sid):
    return oc.context(sid)
