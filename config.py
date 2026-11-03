"""تحميل الإعدادات من .env مع قيم افتراضية آمنة."""
import os
from pathlib import Path

BASE = Path(__file__).resolve().parent
ENV_FILE = BASE / ".env"
STATE_FILE = BASE / "state.json"
LOG_FILE = BASE / "bridge.log"


def _load():
    cfg = {}
    if ENV_FILE.exists():
        for raw in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            cfg[key.strip()] = val.strip().strip('"').strip("'")
    return cfg


_CFG = _load()

TOKEN = _CFG.get("BOT_TOKEN", "")
OWNER = int(_CFG.get("ALLOWED_ID", "0") or 0)
# مجموعة الموضوعات (Topics): كل جلسة OpenCode في موضوع مستقل. 0 = معطّل.
GROUP_CHAT_ID = int(_CFG.get("GROUP_CHAT_ID", "0") or 0)

DEFAULT_DIR = _CFG.get("QODER_DIR", str(BASE))
QODER = _CFG.get("QODER_BIN", "qoder")
QODER_MODE = _CFG.get("QODER_PERMISSION_MODE", "accept_edits")
QODER_TIMEOUT = int(_CFG.get("QODER_TIMEOUT", "900"))

OPENCODE_BIN = _CFG.get(
    "OPENCODE_BIN",
    r"C:\Users\blals\AppData\Roaming\npm\node_modules\@opencode\cli\bin\opencode.exe",
)
OPENCODE_PROVIDER = _CFG.get("OPENCODE_PROVIDER", "opencode")
OPENCODE_MODEL = _CFG.get("OPENCODE_MODEL", "deepseek-v4.1-flash-free")
OPENCODE_TIMEOUT = int(_CFG.get("OPENCODE_TIMEOUT", "600"))

STREAM_INTERVAL = float(_CFG.get("STREAM_INTERVAL", "1.6"))
