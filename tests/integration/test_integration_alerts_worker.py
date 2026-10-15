"""Integration tests for alert checking background worker."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.database import (
    add_account,
    add_alert,
    get_alerts_by_account,
)
from app.services.alerts import alerts_background_worker, check_alerts_job


@pytest.mark.asyncio
async def test_check_alerts_job_end_to_end(tmp_db_path, mock_bot):
    owner_id = 9999
    acc_id = add_account("IntegrationAcc", "valid_token", tmp_db_path)
    alert_id = add_alert(acc_id, "threshold", 3, 50.0, tmp_db_path)

    quota_data = {
        "limits": [
            {
                "unit": 3,
                "percentage": 85.0,
                "currentValue": 850,
                "usage": 1000,
                "nextResetTime": 1780000000000,
            }
        ]
    }

    with patch("app.services.alerts.check_token", return_value=(True, quota_data)):
        # Run 1: Condition met -> Message should be sent
        triggered = await check_alerts_job(mock_bot, owner_id, db_path=tmp_db_path)
        assert triggered == 1
        mock_bot.send_message.assert_awaited_once()
        sent_text = mock_bot.send_message.call_args[0][1]
        assert "IntegrationAcc" in sent_text
        assert "Порог <b>50%</b> превышен" in sent_text
        assert "850 / 1000 Credits" in sent_text

        # Verify DB updated with nextResetTime
        alerts = get_alerts_by_account(acc_id, tmp_db_path)
        assert alerts[0]["last_triggered_reset_time"] == 1780000000000

        # Run 2: Same reset cycle -> Anti-spam should prevent duplicate notification
        mock_bot.send_message.reset_mock()
        triggered2 = await check_alerts_job(mock_bot, owner_id, db_path=tmp_db_path)
        assert triggered2 == 0
        mock_bot.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_check_alerts_job_empty(tmp_db_path, mock_bot):
    # No alerts in DB
    triggered = await check_alerts_job(mock_bot, 9999, db_path=tmp_db_path)
    assert triggered == 0
    mock_bot.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_alerts_background_worker_lifecycle(tmp_db_path, mock_bot):
    stop_event = asyncio.Event()

    with patch("app.services.alerts.check_alerts_job", new_callable=AsyncMock) as mock_job:
        # Launch worker with short delays and stop event
        worker_task = asyncio.create_task(
            alerts_background_worker(
                bot=mock_bot,
                owner_id=9999,
                check_interval=1,
                initial_delay=0,
                db_path=tmp_db_path,
                stop_event=stop_event,
            )
        )

        await asyncio.sleep(0.05)
        stop_event.set()
        await worker_task

        assert mock_job.await_count >= 1


@pytest.mark.asyncio
async def test_alerts_background_worker_initial_delay_stop(tmp_db_path, mock_bot):
    stop_event = asyncio.Event()
    # Trigger stop during initial delay
    stop_event.set()

    worker_task = asyncio.create_task(
        alerts_background_worker(
            bot=mock_bot,
            owner_id=9999,
            check_interval=60,
            initial_delay=10,
            db_path=tmp_db_path,
            stop_event=stop_event,
        )
    )

    await worker_task
    # Should exit cleanly without waiting 10s


@pytest.mark.asyncio
async def test_check_alerts_job_edge_cases(tmp_db_path, mock_bot):
    # 1. Alert referencing deleted account
    acc_id = add_account("ToDel", "tok", tmp_db_path)
    add_alert(acc_id, "threshold", 3, 50.0, tmp_db_path)
    # Manually delete account but leave alert
    with __import__("sqlite3").connect(tmp_db_path) as conn:
        conn.cursor().execute("DELETE FROM accounts WHERE id = ?", (acc_id,))
        conn.commit()

    triggered = await check_alerts_job(mock_bot, 9999, db_path=tmp_db_path)
    assert triggered == 0

    # 2. check_token returns False
    acc_id2 = add_account("Acc2", "tok2", tmp_db_path)
    add_alert(acc_id2, "threshold", 3, 50.0, tmp_db_path)
    with patch("app.services.alerts.check_token", return_value=(False, "API down")):
        triggered = await check_alerts_job(mock_bot, 9999, db_path=tmp_db_path)
        assert triggered == 0

    # 3. check_token returns empty limits
    with patch("app.services.alerts.check_token", return_value=(True, {"limits": []})):
        triggered = await check_alerts_job(mock_bot, 9999, db_path=tmp_db_path)
        assert triggered == 0

    # 4. bot.send_message raises exception
    with patch("app.services.alerts.check_token", return_value=(True, {"limits": [{"unit": 3, "percentage": 90}]})) :
        mock_bot.send_message = AsyncMock(side_effect=Exception("Telegram down"))
        triggered = await check_alerts_job(mock_bot, 9999, db_path=tmp_db_path)
        assert triggered == 0


@pytest.mark.asyncio
async def test_alerts_background_worker_handles_job_exception(tmp_db_path, mock_bot):
    stop_event = asyncio.Event()

    with patch("app.services.alerts.check_alerts_job", side_effect=[Exception("Boom!"), None]) as mock_job:
        worker_task = asyncio.create_task(
            alerts_background_worker(
                bot=mock_bot,
                owner_id=9999,
                check_interval=1,
                initial_delay=0,
                db_path=tmp_db_path,
                stop_event=stop_event,
            )
        )
        await asyncio.sleep(0.05)
        stop_event.set()
        await worker_task
        assert mock_job.call_count >= 1

