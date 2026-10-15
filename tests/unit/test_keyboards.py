"""Unit tests for app/keyboards.py."""

from app.keyboards import (
    get_account_added_kb,
    get_account_shares_management_kb,
    get_account_view_kb,
    get_accounts_list_kb,
    get_add_alert_menu_kb,
    get_admin_menu_kb,
    get_admin_user_detail_kb,
    get_admin_users_kb,
    get_alert_saved_kb,
    get_alerts_list_kb,
    get_author_info_kb,
    get_custom_unit_choice_kb,
    get_empty_accounts_kb,
    get_main_menu_kb,
    get_pick_user_to_share_kb,
    get_share_accounts_list_kb,
)


def test_keyboards_structure():
    # User menu without admin button
    user_kb = get_main_menu_kb(is_admin=False)
    assert not any("admin_menu" in btn.callback_data for row in user_kb.inline_keyboard for btn in row)

    # Admin menu has admin button
    admin_kb = get_main_menu_kb(is_admin=True)
    assert any("admin_menu" in btn.callback_data for row in admin_kb.inline_keyboard for btn in row)

    author_kb = get_author_info_kb()
    assert author_kb.inline_keyboard[0][0].callback_data == "start_menu"

    empty_kb = get_empty_accounts_kb()
    assert empty_kb.inline_keyboard[0][0].callback_data == "add_acc"

    accounts = [{"id": 1, "name": "Work", "is_shared": False}, {"id": 2, "name": "Shared", "is_shared": True}]
    accs_kb = get_accounts_list_kb(accounts)
    assert len(accs_kb.inline_keyboard) == 3
    assert accs_kb.inline_keyboard[0][0].text == "📊 Work"
    assert accs_kb.inline_keyboard[1][0].text == "👥 Shared"

    # View KB for owner vs non-owner
    owner_view_kb = get_account_view_kb(42, is_owner=True, is_admin=False)
    assert any("del_42" in btn.callback_data for row in owner_view_kb.inline_keyboard for btn in row)
    assert any("accshare_42" in btn.callback_data for row in owner_view_kb.inline_keyboard for btn in row)

    guest_view_kb = get_account_view_kb(42, is_owner=False, is_admin=False)
    assert not any("del_42" in btn.callback_data for row in guest_view_kb.inline_keyboard for btn in row)
    assert not any("accshare_42" in btn.callback_data for row in guest_view_kb.inline_keyboard for btn in row)

    alerts = [
        {"id": 10, "limit_unit": 3, "alert_type": "threshold", "threshold_pct": 75.0},
        {"id": 11, "limit_unit": 6, "alert_type": "burn_rate", "threshold_pct": 50.0},
    ]
    alerts_kb = get_alerts_list_kb(42, alerts)
    assert len(alerts_kb.inline_keyboard) == 4
    assert alerts_kb.inline_keyboard[0][0].callback_data == "delalert_10_42"
    assert alerts_kb.inline_keyboard[1][0].callback_data == "delalert_11_42"

    add_alert_kb = get_add_alert_menu_kb(42)
    assert any("setalt_42_threshold_3_50" in btn.callback_data for row in add_alert_kb.inline_keyboard for btn in row)

    custom_unit_kb = get_custom_unit_choice_kb(42)
    assert custom_unit_kb.inline_keyboard[0][0].callback_data == "customchoose_42_3"

    saved_kb = get_alert_saved_kb(42)
    assert saved_kb.inline_keyboard[0][0].callback_data == "alerts_42"

    added_kb = get_account_added_kb()
    assert added_kb.inline_keyboard[0][0].callback_data == "start_menu"


def test_admin_keyboards_structure():
    adm_kb = get_admin_menu_kb()
    assert any("admin_users" in btn.callback_data for row in adm_kb.inline_keyboard for btn in row)

    users = [
        {"user_id": 1, "username": "alice", "is_approved": True},
        {"user_id": 2, "username": "bob", "is_approved": False},
    ]
    usr_kb = get_admin_users_kb(users)
    assert len(usr_kb.inline_keyboard) == 3
    assert usr_kb.inline_keyboard[0][0].callback_data == "adm_usr_1"

    detail_approved_kb = get_admin_user_detail_kb(1, is_approved=True)
    assert any("adm_rejc_1" in btn.callback_data for row in detail_approved_kb.inline_keyboard for btn in row)

    detail_pending_kb = get_admin_user_detail_kb(2, is_approved=False)
    assert any("adm_appr_2" in btn.callback_data for row in detail_pending_kb.inline_keyboard for btn in row)

    share_accs_kb = get_share_accounts_list_kb([{"id": 5, "name": "Corp"}])
    assert share_accs_kb.inline_keyboard[0][0].callback_data == "accshare_5"

    shares_manage_kb = get_account_shares_management_kb(
        5, shared_users=[{"user_id": 10, "username": "shared_user"}], has_available_users=True
    )
    assert any("unshare_5_10" in btn.callback_data for row in shares_manage_kb.inline_keyboard for btn in row)
    assert any("sharepick_5" in btn.callback_data for row in shares_manage_kb.inline_keyboard for btn in row)

    pick_kb = get_pick_user_to_share_kb(5, [{"user_id": 11, "username": "new_user"}])
    assert pick_kb.inline_keyboard[0][0].callback_data == "doshare_5_11"
