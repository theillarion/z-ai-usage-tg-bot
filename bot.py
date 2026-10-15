"""Backward-compatible entrypoint and interface for Z.ai Usage Telegram Bot."""

import logging
from aiogram import Bot, Dispatcher

from app.config import config
from app.database import (
    add_account,
    add_alert,
    delete_account,
    delete_alert,
    get_account_by_id,
    get_accounts,
    get_alerts_by_account,
    get_all_alerts,
    init_db,
    update_alert_triggered,
)
from app.formatters import format_limits_text, format_ts_msk
from app.handlers import get_main_router
from app.main import create_bot, create_dispatcher, main
from app.middlewares import AuthMiddleware
from app.services.alerts import alerts_background_worker, check_alerts_job
from app.states import AddAccountFSM, CustomAlertFSM
from app.zai_client import check_token

BOT_TOKEN = config.BOT_TOKEN
OWNER_ID = config.OWNER_ID

# Module-level instances for backward compatibility
router = get_main_router()
dp = create_dispatcher(OWNER_ID)
bot: Bot = create_bot(BOT_TOKEN) if BOT_TOKEN else None

__all__ = [
    "BOT_TOKEN",
    "OWNER_ID",
    "bot",
    "dp",
    "router",
    "main",
    "init_db",
    "add_account",
    "get_accounts",
    "get_account_by_id",
    "delete_account",
    "add_alert",
    "get_alerts_by_account",
    "get_all_alerts",
    "update_alert_triggered",
    "delete_alert",
    "format_ts_msk",
    "format_limits_text",
    "check_token",
    "check_alerts_job",
    "alerts_background_worker",
    "AddAccountFSM",
    "CustomAlertFSM",
    "AuthMiddleware",
]

if __name__ == "__main__":
    main()
