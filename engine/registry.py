"""سجل مؤقت: يخزّن بيانات الأزرار خلف مفاتيح قصيرة (حد تيليجرام 64 بايت)."""
import itertools
import threading
import time

TTL = 3600
_SEQ = itertools.count(1)
_DATA = {}
_LOCK = threading.Lock()


def _prune():
    now = time.time()
    for key in [k for k, (_, exp) in _DATA.items() if exp < now]:
        _DATA.pop(key, None)


def put(payload, ttl=TTL):
    key = f"k{next(_SEQ)}"
    with _LOCK:
        _DATA[key] = (payload, time.time() + ttl)
        if len(_DATA) > 400:
            _prune()
    return key


def get(key):
    with _LOCK:
        item = _DATA.get(key)
        if not item:
            return None
        payload, exp = item
        if exp < time.time():
            _DATA.pop(key, None)
            return None
        return payload


def drop(key):
    with _LOCK:
        _DATA.pop(key, None)
