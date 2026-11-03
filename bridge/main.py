"""نقطة الدخول: تحميل الإعدادات، بناء السياق، ثم استطلاع تيليجرام."""
from __future__ import annotations

import config
from bridge.container import Context
from bridge.infrastructure.telegram.client import Telegram
from bridge.infrastructure.telegram.poller import TelegramPoller
from bridge.shared.logging_setup import configure_logging, get_logger


def main() -> int:
    configure_logging()
    log = get_logger("main")
    if not config.TOKEN or not config.OWNER:
        log.error("BOT_TOKEN أو ALLOWED_ID مفقود في .env")
        return 1
    log.info("بدء البوت | owner=%s | dir=%s", config.OWNER, config.DEFAULT_DIR)
    ctx = Context(Telegram(config.TOKEN), config.OWNER)
    TelegramPoller(ctx).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
