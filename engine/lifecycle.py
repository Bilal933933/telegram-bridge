"""دورة حياة جلسة OpenCode: فتح/إنشاء/حالة — كما يفعل البرنامج الحقيقي."""
import state
from bridge.infrastructure.engines.registry import get as get_engine


def _engine():
    return get_engine("opencode")


def info(sid):
    return _engine().session_info(sid)


def busy(sid):
    return _engine().is_active(sid)


def open(chat_id, sid, directory=None):
    """فتح جلسة قائمة بنفس معرّفها الحقيقي (resume لا نسخة)."""
    data = _engine().session_info(sid)
    directory = directory or (data.get("location") or {}).get("directory")
    state.update(chat_id, src="opencode", oc_session=sid,
                 workdir=directory or state.get(chat_id)["workdir"],
                 project=directory or "")
    return data


def create(chat_id, directory, title=None):
    sid = _engine().create_session(directory, title or "تيليجرام")
    state.update(chat_id, src="opencode", oc_session=sid,
                 workdir=directory, project=directory)
    return sid


def switch_agent(sid, agent_id):
    return _engine().set_agent(sid, agent_id)


def switch_model(sid, model_id, provider=""):
    return _engine().set_model(sid, model_id, provider)


def history(sid):
    return _engine().context(sid)
