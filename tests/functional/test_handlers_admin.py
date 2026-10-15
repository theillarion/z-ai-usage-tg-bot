"""Functional tests for admin panel and account sharing handlers."""

from unittest.mock import AsyncMock, MagicMock
import pytest
from aiogram.types import CallbackQuery, Message, User

from app.database import (
    add_account,
    get_shared_users_for_account,
    get_user,
    share_account,
    upsert_user,
)
from app.handlers.admin import (
    account_share_manage_cb,
    admin_approve_cb,
    admin_menu_cb,
    admin_reject_cb,
    admin_shares_cb,
    admin_user_detail_cb,
    admin_users_cb,
    do_share_account_cb,
    share_pick_user_cb,
    unshare_account_cb,
)


def _make_cb(user_id: int, data: str = "") -> MagicMock:
    cb = MagicMock(spec=CallbackQuery)
    cb.data = data
    cb.from_user = MagicMock(spec=User)
    cb.from_user.id = user_id
    cb.message = MagicMock(spec=Message)
    cb.message.edit_text = AsyncMock()
    cb.answer = AsyncMock()
    return cb


@pytest.mark.asyncio
async def test_admin_menu_cb(tmp_db_path, monkeypatch):
    monkeypatch.setattr("app.config.config.DB_PATH", tmp_db_path)
    monkeypatch.setattr("app.config.config.OWNER_ID", 111)

    # 1. Non-admin denied
    cb_guest = _make_cb(222, "admin_menu")
    await admin_menu_cb(cb_guest)
    cb_guest.answer.assert_awaited_with("Доступ запрещен.", show_alert=True)

    # 2. Owner allowed
    cb_admin = _make_cb(111, "admin_menu")
    await admin_menu_cb(cb_admin)
    cb_admin.message.edit_text.assert_awaited_once()
    assert "Панель администратора" in cb_admin.message.edit_text.call_args[0][0]


@pytest.mark.asyncio
async def test_admin_users_cb(tmp_db_path, monkeypatch):
    monkeypatch.setattr("app.config.config.DB_PATH", tmp_db_path)
    monkeypatch.setattr("app.config.config.OWNER_ID", 111)

    upsert_user(222, "guest_user", "Guest", is_approved=0, db_path=tmp_db_path)
    cb = _make_cb(111, "admin_users")

    await admin_users_cb(cb)
    cb.message.edit_text.assert_awaited_once()
    assert "Управление пользователями" in cb.message.edit_text.call_args[0][0]


@pytest.mark.asyncio
async def test_admin_user_detail_cb(tmp_db_path, monkeypatch):
    monkeypatch.setattr("app.config.config.DB_PATH", tmp_db_path)
    monkeypatch.setattr("app.config.config.OWNER_ID", 111)

    upsert_user(222, "target", "Target", is_approved=1, db_path=tmp_db_path)

    # Found
    cb = _make_cb(111, "adm_usr_222")
    await admin_user_detail_cb(cb)
    cb.message.edit_text.assert_awaited_once()
    assert "@target" in cb.message.edit_text.call_args[0][0]

    # Not found
    cb_missing = _make_cb(111, "adm_usr_9999")
    await admin_user_detail_cb(cb_missing)
    cb_missing.answer.assert_awaited_with("Пользователь не найден", show_alert=True)


@pytest.mark.asyncio
async def test_admin_approve_and_reject(tmp_db_path, monkeypatch, mock_bot):
    monkeypatch.setattr("app.config.config.DB_PATH", tmp_db_path)
    monkeypatch.setattr("app.config.config.OWNER_ID", 111)

    upsert_user(222, "pending_user", "Pending", is_approved=0, db_path=tmp_db_path)

    # Approve
    cb_appr = _make_cb(111, "adm_appr_222")
    await admin_approve_cb(cb_appr, mock_bot)
    assert get_user(222, tmp_db_path)["is_approved"] is True
    mock_bot.send_message.assert_awaited_once()
    assert "заявка одобрена" in mock_bot.send_message.call_args[0][1]
    cb_appr.message.edit_text.assert_awaited_once()

    # Second click on Approve (idempotent: does NOT send duplicate message)
    mock_bot.send_message.reset_mock()
    cb_appr_dup = _make_cb(111, "adm_appr_222")
    await admin_approve_cb(cb_appr_dup, mock_bot)
    mock_bot.send_message.assert_not_awaited()
    cb_appr_dup.answer.assert_awaited_with("Пользователь уже одобрен.")

    # Reject
    mock_bot.send_message.reset_mock()
    cb_rejc = _make_cb(111, "adm_rejc_222")
    await admin_reject_cb(cb_rejc, mock_bot)
    assert get_user(222, tmp_db_path)["is_approved"] is False
    mock_bot.send_message.assert_awaited_once()
    assert "отозван" in mock_bot.send_message.call_args[0][1]
    cb_rejc.message.edit_text.assert_awaited_once()

    # Second click on Reject (idempotent: does NOT send duplicate message)
    # Missing user tests
    cb_appr_missing = _make_cb(111, "adm_appr_99999")
    await admin_approve_cb(cb_appr_missing, mock_bot)
    cb_appr_missing.answer.assert_awaited_with("Пользователь не найден", show_alert=True)

    cb_rejc_missing = _make_cb(111, "adm_rejc_99999")
    await admin_reject_cb(cb_rejc_missing, mock_bot)
    cb_rejc_missing.answer.assert_awaited_with("Пользователь не найден", show_alert=True)




@pytest.mark.asyncio
async def test_admin_shares_cb(tmp_db_path, monkeypatch):
    monkeypatch.setattr("app.config.config.DB_PATH", tmp_db_path)
    monkeypatch.setattr("app.config.config.OWNER_ID", 111)

    add_account("Corp", "token", user_id=111, db_path=tmp_db_path)
    cb = _make_cb(111, "admin_shares")

    await admin_shares_cb(cb)
    cb.message.edit_text.assert_awaited_once()
    assert "Управление доступом к токенам" in cb.message.edit_text.call_args[0][0]


@pytest.mark.asyncio
async def test_account_share_manage_and_pick(tmp_db_path, monkeypatch):
    monkeypatch.setattr("app.config.config.DB_PATH", tmp_db_path)
    monkeypatch.setattr("app.config.config.OWNER_ID", 111)

    acc_id = add_account("OwnerAcc", "tok", user_id=111, db_path=tmp_db_path)
    upsert_user(222, "approved_dev", "Dev", is_approved=1, db_path=tmp_db_path)

    # 1. Manage shares (currently empty)
    cb_manage = _make_cb(111, f"accshare_{acc_id}")
    await account_share_manage_cb(cb_manage)
    cb_manage.message.edit_text.assert_awaited_once()
    assert "ни у кого нет доступа" in cb_manage.message.edit_text.call_args[0][0]

    # 2. Pick user to share with
    cb_pick = _make_cb(111, f"sharepick_{acc_id}")
    await share_pick_user_cb(cb_pick)
    cb_pick.message.edit_text.assert_awaited_once()
    assert "Кому выдать доступ" in cb_pick.message.edit_text.call_args[0][0]

    # 3. Unauthorized user cannot manage shares
    cb_unauth = _make_cb(333, f"accshare_{acc_id}")
    await account_share_manage_cb(cb_unauth)
    cb_unauth.answer.assert_awaited_with("У вас нет прав на управление доступом к этому аккаунту", show_alert=True)


@pytest.mark.asyncio
async def test_do_share_and_unshare(tmp_db_path, monkeypatch, mock_bot):
    monkeypatch.setattr("app.config.config.DB_PATH", tmp_db_path)
    monkeypatch.setattr("app.config.config.OWNER_ID", 111)

    acc_id = add_account("MainCorp", "tok", user_id=111, db_path=tmp_db_path)
    upsert_user(222, "approved_dev", "Dev", is_approved=1, db_path=tmp_db_path)

    # Grant access
    cb_do = _make_cb(111, f"doshare_{acc_id}_222")
    await do_share_account_cb(cb_do, mock_bot)
    assert len(get_shared_users_for_account(acc_id, tmp_db_path)) == 1
    mock_bot.send_message.assert_awaited_once()
    assert "открыт доступ" in mock_bot.send_message.call_args[0][1]

    # Revoke access
    mock_bot.send_message.reset_mock()
    cb_un = _make_cb(111, f"unshare_{acc_id}_222")
    await unshare_account_cb(cb_un, mock_bot)
    assert len(get_shared_users_for_account(acc_id, tmp_db_path)) == 0
    mock_bot.send_message.assert_awaited_once()
    assert "закрыт владельцем" in mock_bot.send_message.call_args[0][1]


@pytest.mark.asyncio
async def test_admin_handlers_denied_for_guests(tmp_db_path, monkeypatch, mock_bot):
    monkeypatch.setattr("app.config.config.DB_PATH", tmp_db_path)
    monkeypatch.setattr("app.config.config.OWNER_ID", 111)

    cb_guest = _make_cb(999)

    await admin_users_cb(cb_guest)
    cb_guest.answer.assert_awaited_with("Доступ запрещен.", show_alert=True)

    await admin_user_detail_cb(cb_guest)
    cb_guest.answer.assert_awaited_with("Доступ запрещен.", show_alert=True)

    await admin_approve_cb(cb_guest, mock_bot)
    cb_guest.answer.assert_awaited_with("Доступ запрещен.", show_alert=True)

    await admin_reject_cb(cb_guest, mock_bot)
    cb_guest.answer.assert_awaited_with("Доступ запрещен.", show_alert=True)

    await admin_shares_cb(cb_guest)
    cb_guest.answer.assert_awaited_with("Доступ запрещен.", show_alert=True)

    cb_guest.data = "sharepick_42"
    await share_pick_user_cb(cb_guest)
    cb_guest.answer.assert_awaited_with("У вас нет прав", show_alert=True)

    cb_guest.data = "doshare_42_999"
    await do_share_account_cb(cb_guest, mock_bot)
    cb_guest.answer.assert_awaited_with("У вас нет прав", show_alert=True)

    cb_guest.data = "unshare_42_999"
    await unshare_account_cb(cb_guest, mock_bot)
    cb_guest.answer.assert_awaited_with("У вас нет прав", show_alert=True)


@pytest.mark.asyncio
async def test_account_share_manage_missing_account(tmp_db_path, monkeypatch):
    monkeypatch.setattr("app.config.config.DB_PATH", tmp_db_path)
    monkeypatch.setattr("app.config.config.OWNER_ID", 111)

    cb = _make_cb(111, "accshare_9999")
    await account_share_manage_cb(cb)
    cb.answer.assert_awaited_with("Аккаунт не найден", show_alert=True)

    cb_pick_missing = _make_cb(111, "sharepick_9999")
    await share_pick_user_cb(cb_pick_missing)
    cb_pick_missing.answer.assert_awaited_with("Аккаунт не найден", show_alert=True)

    acc_id = add_account("Exist", "tok", user_id=111, db_path=tmp_db_path)
    cb_pick_empty = _make_cb(111, f"sharepick_{acc_id}")
    await share_pick_user_cb(cb_pick_empty)
    cb_pick_empty.answer.assert_awaited_with("Нет доступных пользователей для добавления", show_alert=True)


@pytest.mark.asyncio
async def test_admin_share_missing_account_and_exceptions(tmp_db_path, monkeypatch):
    monkeypatch.setattr("app.config.config.DB_PATH", tmp_db_path)
    monkeypatch.setattr("app.config.config.OWNER_ID", 111)

    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock(side_effect=Exception("Network error"))

    # Missing account in do_share and unshare
    cb_missing_doshare = _make_cb(111, "doshare_9999_222")
    await do_share_account_cb(cb_missing_doshare, mock_bot)
    cb_missing_doshare.answer.assert_awaited_with("Аккаунт не найден", show_alert=True)

    cb_missing_unshare = _make_cb(111, "unshare_9999_222")
    await unshare_account_cb(cb_missing_unshare, mock_bot)
    cb_missing_unshare.answer.assert_awaited_with("Аккаунт не найден", show_alert=True)

    # Approve / reject with bot send_message error
    upsert_user(222, "bob", db_path=tmp_db_path)
    cb_app = _make_cb(111, "adm_appr_222")
    await admin_approve_cb(cb_app, mock_bot)
    assert get_user(222, db_path=tmp_db_path)["is_approved"] == 1

    cb_rejc = _make_cb(111, "adm_rejc_222")
    await admin_reject_cb(cb_rejc, mock_bot)
    assert get_user(222, db_path=tmp_db_path)["is_approved"] == 0

    # do_share / unshare with bot send_message error
    acc_id = add_account("TestAcc", "tok", user_id=111, db_path=tmp_db_path)
    cb_share = _make_cb(111, f"doshare_{acc_id}_222")
    await do_share_account_cb(cb_share, mock_bot)
    assert len(get_shared_users_for_account(acc_id, db_path=tmp_db_path)) == 1

    cb_unshare = _make_cb(111, f"unshare_{acc_id}_222")
    await unshare_account_cb(cb_unshare, mock_bot)
    assert len(get_shared_users_for_account(acc_id, db_path=tmp_db_path)) == 0


@pytest.mark.asyncio
async def test_frozen_callback_query_compatibility(tmp_db_path, monkeypatch, mock_bot):
    """Ensure handlers work with frozen Pydantic v2 CallbackQuery models without mutating cb.data."""
    from datetime import datetime
    from aiogram.types import Chat

    monkeypatch.setattr("app.config.config.DB_PATH", tmp_db_path)
    monkeypatch.setattr("app.config.config.OWNER_ID", 111)

    upsert_user(333, "frozen_user", "Frozen", is_approved=0, db_path=tmp_db_path)

    # Real frozen CallbackQuery
    real_cb = CallbackQuery(
        id="cb_real_1",
        from_user=User(id=111, is_bot=False, first_name="Owner"),
        chat_instance="ci_1",
        data="adm_appr_333",
        message=Message(
            message_id=999,
            date=datetime.now(),
            chat=Chat(id=111, type="private"),
            text="🔔 Новый запрос на доступ к боту!",
        ),
    )
    # Mock methods using object.__setattr__ to bypass Pydantic frozen check
    answer_mock = AsyncMock()
    edit_mock = AsyncMock()
    object.__setattr__(real_cb, "answer", answer_mock)
    object.__setattr__(real_cb.message, "edit_text", edit_mock)

    await admin_approve_cb(real_cb, mock_bot)
    assert get_user(333, db_path=tmp_db_path)["is_approved"] is True
    edit_mock.assert_awaited_once()
    assert "✅ Одобрен" in edit_mock.call_args[0][0]





