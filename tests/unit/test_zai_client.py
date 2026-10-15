"""Unit tests for app/zai_client.py."""

from unittest.mock import MagicMock
import requests
from app.zai_client import check_token


def test_check_token_success_with_subscription(sample_quota_data):
    mock_session = MagicMock()

    # Quota response
    quota_resp = MagicMock()
    quota_resp.status_code = 200
    quota_resp.json.return_value = {
        "code": 200,
        "data": {
            "level": "PRO",
            "limits": sample_quota_data["limits"],
        },
    }

    # Subscription list response
    sub_resp = MagicMock()
    sub_resp.status_code = 200
    sub_resp.json.return_value = {
        "code": 200,
        "data": [
            {
                "inCurrentPeriod": True,
                "productName": "GLM Coding Plan",
                "value": "Pro",
                "version": "v3",
                "nextRenewTime": 1780000000000,
                "autoRenew": True,
            }
        ],
    }

    mock_session.get.side_effect = [quota_resp, sub_resp]

    ok, data = check_token("valid_token", session=mock_session)
    assert ok is True
    assert data["level"] == "PRO"
    assert data["plan_title"] == "GLM Coding Plan - Pro (v3)"
    assert data["subscription_end"] == 1780000000000
    assert data["auto_renew"] is True


def test_check_token_header_fallback_recovery():
    mock_session = MagicMock()

    # Attempt 1: empty limits
    resp1 = MagicMock()
    resp1.status_code = 200
    resp1.json.return_value = {"code": 200, "data": {"limits": []}}

    # Attempt 2: valid limits
    resp2 = MagicMock()
    resp2.status_code = 200
    resp2.json.return_value = {
        "code": 200,
        "data": {"limits": [{"type": "CREDIT_LIMIT", "unit": 3, "percentage": 10}]},
    }

    # Sub list response empty
    sub_resp = MagicMock()
    sub_resp.status_code = 200
    sub_resp.json.return_value = {"code": 200, "data": []}

    # Legacy sub response empty
    legacy_resp = MagicMock()
    legacy_resp.status_code = 404

    mock_session.get.side_effect = [resp1, resp2, sub_resp, legacy_resp]

    ok, data = check_token("token_with_fallback", session=mock_session)
    assert ok is True
    assert len(data["limits"]) == 1


def test_check_token_all_header_attempts_fail():
    mock_session = MagicMock()

    resp = MagicMock()
    resp.status_code = 401
    mock_session.get.return_value = resp

    ok, err = check_token("bad_token", session=mock_session)
    assert ok is False
    assert "HTTP Error 401" in err


def test_check_token_api_error_code():
    mock_session = MagicMock()

    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"code": 403, "msg": "Access Denied"}
    mock_session.get.return_value = resp

    ok, err = check_token("unauthorized_token", session=mock_session)
    assert ok is False
    assert err == "Access Denied"


def test_check_token_network_exception():
    mock_session = MagicMock()
    mock_session.get.side_effect = requests.ConnectionError("Connection timed out")

    ok, err = check_token("timeout_token", session=mock_session)
    assert ok is False
    assert "Connection timed out" in err


def test_check_token_subscription_valid_regex_and_legacy_fallback():
    mock_session = MagicMock()

    # Quota response
    quota_resp = MagicMock()
    quota_resp.status_code = 200
    quota_resp.json.return_value = {
        "code": 200,
        "data": {"limits": [{"unit": 3, "percentage": 50}]},
    }

    # Sub list response with regex date in 'valid'
    sub_resp = MagicMock()
    sub_resp.status_code = 200
    sub_resp.json.return_value = {
        "code": 200,
        "data": [
            {
                "productName": "GLM Plan",
                "valid": "2026-01-01 00:00:00 to 2026-12-31 23:59:59",
                "autoRenew": False,
            }
        ],
    }

    mock_session.get.side_effect = [quota_resp, sub_resp]

    ok, data = check_token("regex_sub_token", session=mock_session)
    assert ok is True
    assert data["subscription_end"] == "2026-12-31 23:59:59"


def test_check_token_legacy_sub_fallback():
    mock_session = MagicMock()

    # Quota response
    quota_resp = MagicMock()
    quota_resp.status_code = 200
    quota_resp.json.return_value = {
        "code": 200,
        "data": {"limits": [{"unit": 3, "percentage": 50}]},
    }

    # Sub list returns no valid expiry
    sub_resp = MagicMock()
    sub_resp.status_code = 500

    # Legacy endpoint returns expire_at
    legacy_resp = MagicMock()
    legacy_resp.status_code = 200
    legacy_resp.json.return_value = {
        "code": 0,
        "data": {"expire_at": "2026-11-30 18:00:00"},
    }

    mock_session.get.side_effect = [quota_resp, sub_resp, legacy_resp]

    ok, data = check_token("legacy_token", session=mock_session)
    assert ok is True
    assert data["subscription_end"] == "2026-11-30 18:00:00"


def test_check_token_sub_single_date_regex_and_end_date():
    mock_session = MagicMock()
    quota_resp = MagicMock(status_code=200)
    quota_resp.json.return_value = {"code": 200, "data": {"limits": [{"unit": 3}]}}

    # Case 1: single date match in 'valid'
    sub_resp1 = MagicMock(status_code=200)
    sub_resp1.json.return_value = {
        "code": 200,
        "data": [{"productName": "Plan", "valid": "2026-05-01"}],
    }
    mock_session.get.side_effect = [quota_resp, sub_resp1]
    ok, data = check_token("tok1", session=mock_session)
    assert ok is True
    assert data["subscription_end"] == "2026-05-01"

    # Case 2: subscriptionEndDate fallback
    sub_resp2 = MagicMock(status_code=200)
    sub_resp2.json.return_value = {
        "code": 200,
        "data": [{"productName": "Plan", "subscriptionEndDate": "2026-06-01"}],
    }
    mock_session.get.side_effect = [quota_resp, sub_resp2]
    ok, data = check_token("tok2", session=mock_session)
    assert ok is True
    assert data["subscription_end"] == "2026-06-01"


def test_check_token_sub_exceptions_handled():
    mock_session = MagicMock()
    quota_resp = MagicMock(status_code=200)
    quota_resp.json.return_value = {"code": 200, "data": {"limits": [{"unit": 3}]}}

    # First sub call raises Exception
    # Second sub call (legacy) raises Exception
    mock_session.get.side_effect = [
        quota_resp,
        Exception("Sub list failed"),
        Exception("Legacy sub failed"),
    ]

    ok, data = check_token("tok_err", session=mock_session)
    assert ok is True
    assert data["subscription_end"] is None

