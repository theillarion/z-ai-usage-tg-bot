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


def test_users_crud(tmp_db_path):
    from app.database import get_all_users, get_pending_users, get_user, set_user_approval, upsert_user

    upsert_user(1001, "alice", "Alice", is_approved=0, is_admin=0, db_path=tmp_db_path)
    upsert_user(1002, "bob", "Bob", is_approved=1, is_admin=0, db_path=tmp_db_path)

    u1 = get_user(1001, tmp_db_path)
    assert u1 is not None
    assert u1["username"] == "alice"
    assert u1["is_approved"] is False

    pending = get_pending_users(tmp_db_path)
    assert len(pending) == 1
    assert pending[0]["user_id"] == 1001

    all_users = get_all_users(tmp_db_path)
    assert len(all_users) >= 2

    set_user_approval(1001, 1, tmp_db_path)
    u1_updated = get_user(1001, tmp_db_path)
    assert u1_updated["is_approved"] is True
    assert get_pending_users(tmp_db_path) == []


def test_account_sharing_and_access(tmp_db_path):
    from app.database import (
        check_account_access,
        get_shared_users_for_account,
        share_account,
        unshare_account,
        upsert_user,
    )

    upsert_user(2001, "owner_user", "Owner", is_approved=1, db_path=tmp_db_path)
    upsert_user(2002, "colleague", "Colleague", is_approved=1, db_path=tmp_db_path)

    acc_id = add_account("SharedCorp", "token_corp", user_id=2001, db_path=tmp_db_path)

    # Owner access check
    has_access, is_owner = check_account_access(acc_id, 2001, tmp_db_path)
    assert has_access is True
    assert is_owner is True

    # Colleague before sharing
    has_access, is_owner = check_account_access(acc_id, 2002, tmp_db_path)
    assert has_access is False
    assert is_owner is False

    # Share account
    share_account(acc_id, 2002, tmp_db_path)
    has_access, is_owner = check_account_access(acc_id, 2002, tmp_db_path)
    assert has_access is True
    assert is_owner is False  # Access granted, but not owner

    shared_users = get_shared_users_for_account(acc_id, tmp_db_path)
    assert len(shared_users) == 1
    assert shared_users[0]["user_id"] == 2002

    # Query accounts for colleague -> should see shared account
    colleague_accs = get_accounts(user_id=2002, db_path=tmp_db_path)
    assert len(colleague_accs) == 1
    assert colleague_accs[0]["name"] == "SharedCorp"
    assert colleague_accs[0]["is_shared"] is True

    # Colleague adds alert
    add_alert(acc_id, "threshold", 3, 50.0, user_id=2002, db_path=tmp_db_path)
    colleague_alerts = get_alerts_by_account(acc_id, user_id=2002, db_path=tmp_db_path)
    assert len(colleague_alerts) == 1

    # Unshare account -> colleague loses access and colleague's alerts are cleaned up
    unshare_account(acc_id, 2002, tmp_db_path)
    has_access, _ = check_account_access(acc_id, 2002, tmp_db_path)
    assert has_access is False
    assert get_alerts_by_account(acc_id, user_id=2002, db_path=tmp_db_path) == []

    # Non-existent account check
    has_access, is_owner = check_account_access(99999, 2001, tmp_db_path)
    assert has_access is False
    assert is_owner is False

