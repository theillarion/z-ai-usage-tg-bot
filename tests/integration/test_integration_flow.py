"""Integration tests for end-to-end bot lifecycle and dispatcher."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.config import Config
from app.database import (
    get_account_by_id,
    get_accounts,
    get_alerts_by_account,
)
from app.handlers import get_main_router
from app.handlers.accounts import add_acc_name, add_acc_token
from app.handlers.alerts import custom_alert_pct_input
from app.main import create_bot, create_dispatcher, run_bot
from app.middlewares import AuthMiddleware
from app.states import AddAccountFSM, CustomAlertFSM


@pytest.mark.asyncio
async def test_dispatcher_and_router_setup():
    owner_id = 77777
    dp = create_dispatcher(owner_id)
    assert len(dp.message.middleware) >= 1
    assert any(isinstance(m, AuthMiddleware) for m in dp.message.middleware)
    assert dp.sub_routers


@pytest.mark.asyncio
async def test_full_account_and_alert_flow(tmp_db_path, mock_fsm_context, monkeypatch):
    monkeypatch.setattr("app.config.config.DB_PATH", tmp_db_path)

    # 1. User submits token
    msg_token = MagicMock()
    msg_token.text = "secret_api_key_123"
    progress_msg = MagicMock()
    progress_msg.edit_text = AsyncMock()
    msg_token.answer = AsyncMock(return_value=progress_msg)

    with patch("app.handlers.accounts.check_token", return_value=(True, {"limits": []})):
        await add_acc_token(msg_token, mock_fsm_context)

    assert await mock_fsm_context.get_state() == AddAccountFSM.name.state

    # 2. User submits name
    msg_name = MagicMock()
    msg_name.text = "Work Account"
    msg_name.answer = AsyncMock()

    await add_acc_name(msg_name, mock_fsm_context)

    accounts = get_accounts(tmp_db_path)
    assert len(accounts) == 1
    acc_id = accounts[0]["id"]
    assert accounts[0]["name"] == "Work Account"

    # 3. User configures a custom alert (60%)
    await mock_fsm_context.update_data(acc_id=acc_id, unit=3)
    await mock_fsm_context.set_state(CustomAlertFSM.pct)

    msg_pct = MagicMock()
    msg_pct.text = "60"
    msg_pct.answer = AsyncMock()

    await custom_alert_pct_input(msg_pct, mock_fsm_context)

    alerts = get_alerts_by_account(acc_id, tmp_db_path)
    assert len(alerts) == 1
    assert alerts[0]["threshold_pct"] == 60.0
    assert alerts[0]["limit_unit"] == 3


@pytest.mark.asyncio
async def test_run_bot_lifecycle(tmp_db_path):
    cfg = Config(
        BOT_TOKEN="123456:FAKE_BOT_TOKEN_FOR_TESTING",
        OWNER_ID=111111,
        DB_DIR="/tmp",
        DB_PATH=tmp_db_path,
        ALERT_CHECK_INTERVAL=1,
        ALERT_WORKER_INITIAL_DELAY=0,
    )

    stop_event = asyncio.Event()

    mock_bot_instance = MagicMock()
    mock_bot_instance.delete_webhook = AsyncMock()
    mock_bot_instance.session = MagicMock()
    mock_bot_instance.session.close = AsyncMock()

    with patch("app.main.create_bot", return_value=mock_bot_instance):
        with patch("aiogram.Dispatcher.start_polling", new_callable=AsyncMock) as mock_poll:
            # When start_polling is called, signal stop_event and return
            async def mock_start_polling(bot):
                stop_event.set()

            mock_poll.side_effect = mock_start_polling

            await run_bot(cfg=cfg, stop_event=stop_event)

            mock_bot_instance.delete_webhook.assert_awaited_once_with(drop_pending_updates=True)
            mock_poll.assert_awaited_once()
            mock_bot_instance.session.close.assert_awaited_once()


def test_create_bot_helper():
    b = create_bot("123456:FAKE_TOKEN")
    assert b.token == "123456:FAKE_TOKEN"


@pytest.mark.asyncio
async def test_run_bot_missing_credentials_exits():
    cfg = Config(
        BOT_TOKEN="",
        OWNER_ID=0,
        DB_DIR="/tmp",
        DB_PATH="/tmp/test.db",
    )
    with pytest.raises(SystemExit):
        await run_bot(cfg=cfg)


def test_main_cli():
    with patch("asyncio.run") as mock_run, patch("app.main.run_bot") as mock_run_bot:
        from app.main import main
        main()
        mock_run.assert_called_once()


