"""Application entrypoint and runtime bootstrap."""

import asyncio
import logging
import sys
from typing import Optional
from aiogram import Bot, Dispatcher

from app.config import Config, config as app_config
from app.database import init_db
from app.handlers import get_main_router
from app.middlewares import AuthMiddleware
from app.services.alerts import alerts_background_worker


def create_bot(token: str) -> Bot:
    """Instantiate Aiogram Bot."""
    return Bot(token=token)


def create_dispatcher(owner_id: int) -> Dispatcher:
    """Instantiate and configure Dispatcher with middlewares and routers."""
    dp = Dispatcher()
    auth_middleware = AuthMiddleware(owner_id=owner_id)
    dp.message.middleware(auth_middleware)
    dp.callback_query.middleware(auth_middleware)
    dp.include_router(get_main_router())
    return dp


async def run_bot(cfg: Optional[Config] = None, stop_event: Optional[asyncio.Event] = None):
    """Start the bot polling and background alert worker."""
    cfg = cfg or app_config
    if not cfg.BOT_TOKEN or not cfg.OWNER_ID:
        logging.error("BOT_TOKEN and OWNER_ID must be set!")
        sys.exit(1)

    init_db(cfg.DB_PATH)
    bot = create_bot(cfg.BOT_TOKEN)
    dp = create_dispatcher(cfg.OWNER_ID)

    await bot.delete_webhook(drop_pending_updates=True)
    worker_task = asyncio.create_task(
        alerts_background_worker(
            bot=bot,
            owner_id=cfg.OWNER_ID,
            check_interval=cfg.ALERT_CHECK_INTERVAL,
            initial_delay=cfg.ALERT_WORKER_INITIAL_DELAY,
            db_path=cfg.DB_PATH,
            stop_event=stop_event,
        )
    )

    try:
        await dp.start_polling(bot)
    finally:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
        await bot.session.close()


def main():
    """Main CLI entrypoint."""
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
