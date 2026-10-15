"""Unit tests for app/formatters.py."""

from unittest.mock import patch
import pytest
from app.formatters import format_limits_text, format_ts_msk


def test_format_ts_msk_empty():
    assert format_ts_msk(None) == "Неизвестно"
    assert format_ts_msk(0) == "Неизвестно"
    assert format_ts_msk("") == "Неизвестно"


def test_format_ts_msk_valid_timestamps():
    # Milliseconds
    ts_ms = 1700000000000  # 2023-11-14 22:13:20 UTC -> 2023-11-15 01:13:20 MSK
    result_ms = format_ts_msk(ts_ms)
    assert "МСК" in result_ms
    assert "2023" in result_ms

    # Seconds
    ts_sec = 1700000000
    result_sec = format_ts_msk(ts_sec)
    assert "МСК" in result_sec
    assert "2023" in result_sec

    # String timestamp
    str_ts = "2025-10-15 15:30:00"
    assert format_ts_msk(str_ts) == str_ts


def test_format_ts_msk_pytz_fallback():
    # Force pytz.timezone to raise an exception, testing fallback to timedelta(hours=3)
    with patch("pytz.timezone", side_effect=Exception("Pytz failed")):
        res = format_ts_msk(1700000000000)
        assert "МСК" in res
        assert "2023" in res


def test_format_ts_msk_total_fallback():
    # When both conversions fail
    with patch("pytz.timezone", side_effect=Exception("Pytz failed")):
        with patch("app.formatters.datetime") as mock_dt:
            mock_dt.fromtimestamp.side_effect = Exception("Datetime failed")
            res = format_ts_msk(1700000000000)
            assert res == "1700000000000"


def test_format_limits_text_no_limits():
    data = {"level": "PRO", "limits": []}
    text = format_limits_text("MainAcc", data)
    assert "📊 <b>Аккаунт:</b> MainAcc" in text
    assert "🔹 <b>Подписка:</b> PRO" in text
    assert "<i>Лимиты не найдены.</i>" in text


def test_format_limits_text_with_plan_title_and_sub_end():
    data = {
        "level": "PRO",
        "plan_title": "GLM Coding Plan - Pro (v3)",
        "subscription_end": 1780000000000,
        "auto_renew": True,
        "limits": [],
    }
    text = format_limits_text("Account1", data)
    assert "GLM Coding Plan - Pro (v3)" in text
    assert "автопродление" in text


def test_format_limits_text_no_plan_title_unknown_level():
    data = {
        "level": "UNKNOWN",
        "limits": [],
    }
    text = format_limits_text("Account1", data)
    assert "🔹 <b>Подписка:</b> Активна" in text


def test_format_limits_text_credit_limit():
    data = {
        "limits": [
            {
                "type": "CREDIT_LIMIT",
                "unit": 3,
                "number": 5,
                "percentage": 50,
                "currentValue": 500,
                "usage": 1000,
                "nextResetTime": 1780000000000,
            },
            {
                "type": "CREDIT_LIMIT",
                "unit": 6,
                "number": 1,
                "percentage": 10,
                "currentValue": None,
                "usage": 5000,
                "nextResetTime": None,
            },
        ]
    }
    text = format_limits_text("CreditAcc", data)
    assert "⏳ <b>5-часовой лимит:</b> Использовано 50% (500 / 1000 Credits)" in text
    assert "Сброс:" in text
    assert "📅 <b>Недельный лимит:</b> Использовано 10% (лимит: 5000 Credits)" in text


def test_format_limits_text_tokens_limit():
    data = {
        "limits": [
            {
                "type": "TOKENS_LIMIT",
                "unit": 5,
                "number": 2,
                "percentage": 30,
                "currentValue": 300,
                "usage": 1000,
                "nextResetTime": 1780000000000,
            },
            {
                "type": "TOKENS_LIMIT",
                "unit": 1,
                "number": 1,
                "percentage": 0,
                "currentValue": 0,
                "usage": 0,
                "nextResetTime": None,
            },
        ]
    }
    text = format_limits_text("TokensAcc", data)
    assert "🗓 <b>2-месячный лимит:</b> Использовано 30% (300 / 1000 Tokens)" in text
    assert "⏰ <b>Суточный лимит:</b> Использовано 0%" in text


def test_format_limits_text_time_limit_tools():
    data = {
        "limits": [
            {
                "type": "TIME_LIMIT",
                "unit": 1,
                "number": 1,
                "percentage": 25,
                "remaining": 75,
                "usage": 100,
                "nextResetTime": 1780000000000,
                "usageDetails": [
                    {"modelCode": "search-prime", "usage": 15},
                    {"modelCode": "search-prime-claude", "usage": 5},
                    {"modelCode": "web-reader", "usage": 3},
                    {"modelCode": "zread", "usage": 2},
                    {"modelCode": "custom-tool", "usage": 1},
                ],
            },
            {
                "type": "TIME_LIMIT",
                "unit": 1,
                "number": 1,
                "percentage": 80,
                "remaining": None,
                "usage": None,
                "nextResetTime": None,
            },
        ]
    }
    text = format_limits_text("ToolsAcc", data)
    assert "🛠 <b>Tools (MCP):</b> Осталось 75 из 100" in text
    assert "Web Search: 15" in text
    assert "Web Search: 5" in text
    assert "Web Reader: 3" in text
    assert "Zread: 2" in text
    assert "custom-tool: 1" in text
    assert "🛠 <b>Tools (MCP):</b> Использовано 80%" in text


def test_format_ts_msk_object_fallback():
    class Dummy:
        def __str__(self):
            return "dummy_ts"

    assert format_ts_msk(Dummy()) == "dummy_ts"


def test_format_limits_text_level_appended_to_plan():
    data = {
        "level": "PREMIUM",
        "plan_title": "GLM Plan",
        "limits": [],
    }
    text = format_limits_text("Acc", data)
    assert "GLM Plan (PREMIUM)" in text


def test_format_limits_text_unknown_limit_type():
    data = {
        "limits": [
            {
                "type": "SPECIAL_QUOTA",
                "unit": 99,
                "percentage": 12,
                "currentValue": 12,
                "usage": 100,
                "nextResetTime": 1780000000000,
            }
        ]
    }
    text = format_limits_text("CustomQuotaAcc", data)
    assert "⏱ <b>Лимит (unit=99) (SPECIAL_QUOTA):</b> Использовано 12% (12 / 100)" in text
    assert "Сброс:" in text


def test_format_limits_text_no_next_reset():
    data = {
        "limits": [
            {
                "type": "OTHER_QUOTA",
                "unit": 3,
                "percentage": 50,
                "currentValue": 50,
                "usage": 100,
                "nextResetTime": 0,
            }
        ]
    }
    text = format_limits_text("NoResetAcc", data)
    assert "Использовано 50%" in text
    assert "Сброс:" not in text



