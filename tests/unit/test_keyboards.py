"""Unit tests for app/keyboards.py."""

from app.keyboards import (
    get_account_added_kb,
    get_account_view_kb,
    get_accounts_list_kb,
    get_add_alert_menu_kb,
    get_alert_saved_kb,
    get_alerts_list_kb,
    get_author_info_kb,
    get_custom_unit_choice_kb,
    get_empty_accounts_kb,
    get_main_menu_kb,
)


def test_keyboards_structure():
    main_kb = get_main_menu_kb()
    assert len(main_kb.inline_keyboard) == 3
    assert main_kb.inline_keyboard[0][0].callback_data == "add_acc"

    author_kb = get_author_info_kb()
    assert author_kb.inline_keyboard[0][0].callback_data == "start_menu"

    empty_kb = get_empty_accounts_kb()
    assert empty_kb.inline_keyboard[0][0].callback_data == "add_acc"

    accounts = [{"id": 1, "name": "Work"}, {"id": 2, "name": "Personal"}]
    accs_kb = get_accounts_list_kb(accounts)
    assert len(accs_kb.inline_keyboard) == 3
    assert accs_kb.inline_keyboard[0][0].text == "📊 Work"
    assert accs_kb.inline_keyboard[0][0].callback_data == "view_1"

    view_kb = get_account_view_kb(42)
    assert len(view_kb.inline_keyboard) == 2
    assert view_kb.inline_keyboard[0][0].callback_data == "view_42"
    assert view_kb.inline_keyboard[0][1].callback_data == "alerts_42"
    assert view_kb.inline_keyboard[0][2].callback_data == "del_42"

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
