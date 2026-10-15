"""Unit tests for app/database.py."""

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


def test_init_db_idempotent(tmp_db_path):
    # Calling init_db multiple times should not cause errors
    init_db(tmp_db_path)
    init_db(tmp_db_path)
    assert get_accounts(tmp_db_path) == []


def test_accounts_crud(tmp_db_path):
    acc1_id = add_account("First", "token_123", tmp_db_path)
    acc2_id = add_account("Second", "token_456", tmp_db_path)
    assert acc1_id > 0
    assert acc2_id > acc1_id

    accounts = get_accounts(tmp_db_path)
    assert len(accounts) == 2
    assert accounts[0]["name"] == "First"
    assert accounts[1]["token"] == "token_456"

    acc1 = get_account_by_id(acc1_id, tmp_db_path)
    assert acc1 is not None
    assert acc1["name"] == "First"
    assert acc1["token"] == "token_123"

    assert get_account_by_id(9999, tmp_db_path) is None

    delete_account(acc1_id, tmp_db_path)
    assert get_account_by_id(acc1_id, tmp_db_path) is None
    assert len(get_accounts(tmp_db_path)) == 1


def test_alerts_crud(tmp_db_path):
    acc_id = add_account("TestAcc", "token_xyz", tmp_db_path)
    alert1_id = add_alert(acc_id, "threshold", 3, 50.0, tmp_db_path)
    alert2_id = add_alert(acc_id, "burn_rate", 6, 50.0, tmp_db_path)

    alerts = get_alerts_by_account(acc_id, tmp_db_path)
    assert len(alerts) == 2
    assert alerts[0]["alert_type"] == "threshold"
    assert alerts[0]["threshold_pct"] == 50.0
    assert alerts[0]["last_triggered_reset_time"] == 0

    all_alerts = get_all_alerts(tmp_db_path)
    assert len(all_alerts) == 2

    # Update triggered timestamp
    update_alert_triggered(alert1_id, 1780000000000, tmp_db_path)
    updated_alerts = get_alerts_by_account(acc_id, tmp_db_path)
    assert updated_alerts[0]["last_triggered_reset_time"] == 1780000000000

    # Delete single alert
    delete_alert(alert1_id, tmp_db_path)
    assert len(get_alerts_by_account(acc_id, tmp_db_path)) == 1

    # Delete account cascades and deletes alerts
    delete_account(acc_id, tmp_db_path)
    assert get_alerts_by_account(acc_id, tmp_db_path) == []
    assert get_all_alerts(tmp_db_path) == []
