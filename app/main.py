"""Application entrypoint and runtime bootstrap."""

import asyncio
import logging
import sys
import socket
from typing import Optional
from aiogram import Bot, Dispatcher

from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramNetworkError

from app.config import Config, config as app_config
from app.database import init_db
from app.handlers import get_main_router
from app.middlewares import AuthMiddleware
from app.services.alerts import alerts_background_worker


def create_bot(
    token: str,
    proxy: Optional[str] = None,
    api_server: Optional[str] = None,
) -> Bot:
    """Instantiate Aiogram Bot with IPv4 connector and optional proxy."""
    session = AiohttpSession(proxy=proxy, timeout=60.0)
    # Force IPv4 to prevent hanging on misconfigured IPv6 / aiohappyeyeballs in Docker / Linux
    session._connector_init["family"] = socket.AF_INET
    if api_server:
        session.api = TelegramAPIServer.from_base(api_server)


    return Bot(
        token=token,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


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
    bot = create_bot(
        token=cfg.BOT_TOKEN,
        proxy=cfg.TELEGRAM_PROXY,
        api_server=cfg.TELEGRAM_API_SERVER,
    )
    dp = create_dispatcher(cfg.OWNER_ID)

    worker_task = None
    try:
        # Retry delete_webhook with backoff to prevent startup crashes from temporary network blips
        for attempt in range(1, 4):
            try:
                logging.info("Deleting webhook (attempt %d/3)...", attempt)
                await bot.delete_webhook(drop_pending_updates=True)
                logging.info("Webhook deleted successfully.")
                break
            except TelegramNetworkError as e:
                logging.warning("Failed to delete webhook (attempt %d/3): %s", attempt, e)
                if attempt < 3:
                    await asyncio.sleep(2 * attempt)
            except Exception as e:
                logging.warning("Unexpected error during delete_webhook: %s", e)
                break

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

        await dp.start_polling(bot)
    finally:
        if worker_task:
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
