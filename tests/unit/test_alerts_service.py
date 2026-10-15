"""Unit tests for app/services/alerts.py evaluate_alert logic."""

import pytest
from app.services.alerts import evaluate_alert


def test_evaluate_alert_threshold():
    limits = [
        {"unit": 3, "percentage": 82.0, "nextResetTime": 1780000000000, "currentValue": 820, "usage": 1000}
    ]

    # Below threshold
    alert_below = {"limit_unit": 3, "alert_type": "threshold", "threshold_pct": 85.0}
    triggered, reason, _, _, _ = evaluate_alert(alert_below, limits, now_ms=1770000000000)
    assert triggered is False

    # Above threshold
    alert_above = {"limit_unit": 3, "alert_type": "threshold", "threshold_pct": 80.0}
    triggered, reason, next_reset, current_val, usage_val = evaluate_alert(
        alert_above, limits, now_ms=1770000000000
    )
    assert triggered is True
    assert "Порог <b>80%</b> превышен" in reason
    assert next_reset == 1780000000000
    assert current_val == 820
    assert usage_val == 1000


def test_evaluate_alert_burn_rate_5h():
    now_ms = 1000000000000
    # 5h = 18_000_000 ms. Half is 9_000_000 ms.
    # Case A: 12_000_000 ms remaining (less than half elapsed) and pct >= 50 -> Trigger
    next_reset_early = now_ms + 12000000
    limits_early = [{"unit": 3, "percentage": 60.0, "nextResetTime": next_reset_early}]
    alert_burn = {"limit_unit": 3, "alert_type": "burn_rate", "threshold_pct": 50.0}

    triggered, reason, _, _, _ = evaluate_alert(alert_burn, limits_early, now_ms=now_ms)
    assert triggered is True
    assert "Быстрый расход (Burn Rate)" in reason

    # Case B: 5_000_000 ms remaining (more than half elapsed) -> Do not trigger
    next_reset_late = now_ms + 5000000
    limits_late = [{"unit": 3, "percentage": 60.0, "nextResetTime": next_reset_late}]
    triggered, _, _, _, _ = evaluate_alert(alert_burn, limits_late, now_ms=now_ms)
    assert triggered is False

    # Case C: early, but pct < 50% -> Do not trigger
    limits_low_pct = [{"unit": 3, "percentage": 40.0, "nextResetTime": next_reset_early}]
    triggered, _, _, _, _ = evaluate_alert(alert_burn, limits_low_pct, now_ms=now_ms)
    assert triggered is False


def test_evaluate_alert_burn_rate_weekly():
    now_ms = 1000000000000
    # 7 days = 604_800_000 ms. Half is 302_400_000 ms.
    next_reset_early = now_ms + 400000000  # > 302_400_000 ms remaining
    limits = [{"unit": 6, "percentage": 55.0, "nextResetTime": next_reset_early}]
    alert = {"limit_unit": 6, "alert_type": "burn_rate", "threshold_pct": 50.0}

    triggered, reason, _, _, _ = evaluate_alert(alert, limits, now_ms=now_ms)
    assert triggered is True
    assert "Быстрый расход" in reason


def test_evaluate_alert_anti_spam():
    next_reset = 1780000000000
    limits = [{"unit": 3, "percentage": 90.0, "nextResetTime": next_reset}]
    # Alert was already triggered in this reset cycle
    alert = {
        "limit_unit": 3,
        "alert_type": "threshold",
        "threshold_pct": 50.0,
        "last_triggered_reset_time": next_reset,
    }

    triggered, _, _, _, _ = evaluate_alert(alert, limits, now_ms=1770000000000)
    assert triggered is False


def test_evaluate_alert_missing_limit_unit():
    limits = [{"unit": 6, "percentage": 90.0, "nextResetTime": 1780000000000}]
    alert = {"limit_unit": 3, "alert_type": "threshold", "threshold_pct": 50.0}

    triggered, _, _, _, _ = evaluate_alert(alert, limits, now_ms=1770000000000)
    assert triggered is False


@pytest.mark.asyncio
async def test_check_alerts_job_token_exception(tmp_db_path, monkeypatch, mock_bot):
    from unittest.mock import patch
    from app.database import add_account, add_alert
    from app.services.alerts import check_alerts_job

    monkeypatch.setattr("app.config.config.DB_PATH", tmp_db_path)
    acc_id = add_account("FaultyAcc", "bad_token", tmp_db_path)
    add_alert(acc_id, "threshold", 3, 50.0, tmp_db_path)

    with patch("app.services.alerts.check_token", side_effect=RuntimeError("Network explosion")):
        triggered = await check_alerts_job(mock_bot, owner_id=111, db_path=tmp_db_path)
        assert triggered == 0

