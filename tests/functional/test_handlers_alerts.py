"""Functional tests for alert management handlers."""

from unittest.mock import AsyncMock, MagicMock
import pytest
from aiogram.types import CallbackQuery, Message

from app.database import add_account, add_alert, get_alerts_by_account
from app.handlers.alerts import (
    acc_alerts_cb,
    add_alert_menu_cb,
    custom_alert_pct_input,
    custom_choose_cb,
    custom_unit_choice_cb,
    del_alert_cb,
    set_alert_preset_cb,
)
from app.states import CustomAlertFSM


@pytest.mark.asyncio
async def test_acc_alerts_cb_not_found(tmp_db_path, monkeypatch):
    monkeypatch.setattr("app.config.config.DB_PATH", tmp_db_path)
    mock_cb = MagicMock(spec=CallbackQuery)
    mock_cb.data = "alerts_9999"
    mock_cb.answer = AsyncMock()

    await acc_alerts_cb(mock_cb)

    mock_cb.answer.assert_awaited_once_with("Аккаунт не найден", show_alert=True)


@pytest.mark.asyncio
async def test_acc_alerts_cb_empty_and_with_alerts(tmp_db_path, monkeypatch):
    monkeypatch.setattr("app.config.config.DB_PATH", tmp_db_path)
    acc_id = add_account("AlertAcc", "token123", tmp_db_path)

    mock_cb = MagicMock(spec=CallbackQuery)
    mock_cb.data = f"alerts_{acc_id}"
    mock_cb.message = MagicMock(spec=Message)
    mock_cb.message.edit_text = AsyncMock()
    mock_cb.answer = AsyncMock()

    # Empty alerts
    await acc_alerts_cb(mock_cb)
    mock_cb.message.edit_text.assert_awaited_once()
    assert "нет настроенных алертов" in mock_cb.message.edit_text.call_args[0][0]

    # Add both types of alerts
    add_alert(acc_id, "threshold", 3, 80.0, tmp_db_path)
    add_alert(acc_id, "burn_rate", 6, 50.0, tmp_db_path)

    mock_cb.message.edit_text.reset_mock()
    await acc_alerts_cb(mock_cb)

    mock_cb.message.edit_text.assert_awaited_once()
    text = mock_cb.message.edit_text.call_args[0][0]
    assert "5-часовой > 80%" in text
    assert "Недельный Burn Rate (>50% за 2.5д)" in text


@pytest.mark.asyncio
async def test_del_alert_cb(tmp_db_path, monkeypatch):
    monkeypatch.setattr("app.config.config.DB_PATH", tmp_db_path)
    acc_id = add_account("AlertAcc", "token123", tmp_db_path)
    alert_id = add_alert(acc_id, "threshold", 3, 50.0, tmp_db_path)

    mock_cb = MagicMock(spec=CallbackQuery)
    mock_cb.data = f"delalert_{alert_id}_{acc_id}"
    mock_cb.message = MagicMock(spec=Message)
    mock_cb.message.edit_text = AsyncMock()
    mock_cb.answer = AsyncMock()

    await del_alert_cb(mock_cb)

    assert get_alerts_by_account(acc_id, tmp_db_path) == []
    mock_cb.answer.assert_any_await("Алерт удален!")


@pytest.mark.asyncio
async def test_add_alert_menu_cb(tmp_db_path, monkeypatch):
    monkeypatch.setattr("app.config.config.DB_PATH", tmp_db_path)
    acc_id = add_account("AlertAcc", "token123", tmp_db_path)

    mock_cb = MagicMock(spec=CallbackQuery)
    mock_cb.data = f"addalert_{acc_id}"
    mock_cb.message = MagicMock(spec=Message)
    mock_cb.message.edit_text = AsyncMock()
    mock_cb.answer = AsyncMock()

    await add_alert_menu_cb(mock_cb)

    mock_cb.message.edit_text.assert_awaited_once()
    assert "Выберите тип алерта" in mock_cb.message.edit_text.call_args[0][0]


@pytest.mark.asyncio
async def test_add_alert_menu_cb_not_found(tmp_db_path, monkeypatch):
    monkeypatch.setattr("app.config.config.DB_PATH", tmp_db_path)
    mock_cb = MagicMock(spec=CallbackQuery)
    mock_cb.data = "addalert_9999"
    mock_cb.answer = AsyncMock()

    await add_alert_menu_cb(mock_cb)
    mock_cb.answer.assert_awaited_once_with("Аккаунт не найден", show_alert=True)


@pytest.mark.asyncio
async def test_set_alert_preset_cb(tmp_db_path, monkeypatch):
    monkeypatch.setattr("app.config.config.DB_PATH", tmp_db_path)
    acc_id = add_account("AlertAcc", "token123", tmp_db_path)

    # Preset 1: threshold
    mock_cb1 = MagicMock(spec=CallbackQuery)
    mock_cb1.data = f"setalt_{acc_id}_threshold_3_80"
    mock_cb1.message = MagicMock(spec=Message)
    mock_cb1.message.edit_text = AsyncMock()
    mock_cb1.answer = AsyncMock()

    await set_alert_preset_cb(mock_cb1)
    mock_cb1.answer.assert_any_await("Алерт успешно добавлен!")

    # Preset 2: burn rate
    mock_cb2 = MagicMock(spec=CallbackQuery)
    mock_cb2.data = f"setalt_{acc_id}_burn_6_50"
    mock_cb2.message = MagicMock(spec=Message)
    mock_cb2.message.edit_text = AsyncMock()
    mock_cb2.answer = AsyncMock()

    await set_alert_preset_cb(mock_cb2)

    alerts = get_alerts_by_account(acc_id, tmp_db_path)
    assert len(alerts) == 2
    assert alerts[0]["alert_type"] == "threshold"
    assert alerts[1]["alert_type"] == "burn_rate"


@pytest.mark.asyncio
async def test_custom_unit_choice_cb(tmp_db_path, monkeypatch):
    mock_cb = MagicMock(spec=CallbackQuery)
    mock_cb.data = "customunit_42"
    mock_cb.message = MagicMock(spec=Message)
    mock_cb.message.edit_text = AsyncMock()
    mock_cb.answer = AsyncMock()

    await custom_unit_choice_cb(mock_cb)

    mock_cb.message.edit_text.assert_awaited_once()
    assert "Для какого лимита" in mock_cb.message.edit_text.call_args[0][0]


@pytest.mark.asyncio
async def test_custom_choose_cb(mock_fsm_context):
    mock_cb = MagicMock(spec=CallbackQuery)
    mock_cb.data = "customchoose_42_3"
    mock_cb.message = MagicMock(spec=Message)
    mock_cb.message.answer = AsyncMock()
    mock_cb.answer = AsyncMock()

    await custom_choose_cb(mock_cb, mock_fsm_context)

    assert await mock_fsm_context.get_state() == CustomAlertFSM.pct.state
    data = await mock_fsm_context.get_data()
    assert data["acc_id"] == 42
    assert data["unit"] == 3
    mock_cb.message.answer.assert_awaited_once()
    assert "5-часового лимита" in mock_cb.message.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_custom_choose_cb_answer_exception(mock_fsm_context):
    mock_cb = MagicMock(spec=CallbackQuery)
    mock_cb.data = "customchoose_42_3"
    mock_cb.message = MagicMock(spec=Message)
    mock_cb.message.answer = AsyncMock(side_effect=RuntimeError("Cannot send message"))
    mock_cb.answer = AsyncMock()

    await custom_choose_cb(mock_cb, mock_fsm_context)
    mock_cb.answer.assert_awaited_once()



@pytest.mark.asyncio
async def test_custom_alert_pct_input_invalid(mock_fsm_context):
    await mock_fsm_context.set_state(CustomAlertFSM.pct)
    mock_msg = MagicMock(spec=Message)
    mock_msg.answer = AsyncMock()

    # Non-number
    mock_msg.text = "abc"
    await custom_alert_pct_input(mock_msg, mock_fsm_context)
    mock_msg.answer.assert_awaited_with("❌ Пожалуйста, введите корректное число от 1 до 99 (например, 75).")

    # Out of range (< 1)
    mock_msg.text = "0"
    await custom_alert_pct_input(mock_msg, mock_fsm_context)

    # Out of range (> 99)
    mock_msg.text = "100"
    await custom_alert_pct_input(mock_msg, mock_fsm_context)

    assert await mock_fsm_context.get_state() == CustomAlertFSM.pct.state


@pytest.mark.asyncio
async def test_custom_alert_pct_input_valid(mock_fsm_context, tmp_db_path, monkeypatch):
    monkeypatch.setattr("app.config.config.DB_PATH", tmp_db_path)
    acc_id = add_account("TestAcc", "token", tmp_db_path)

    await mock_fsm_context.update_data(acc_id=acc_id, unit=3)
    await mock_fsm_context.set_state(CustomAlertFSM.pct)

    mock_msg = MagicMock(spec=Message)
    mock_msg.text = "75%"
    mock_msg.answer = AsyncMock()

    await custom_alert_pct_input(mock_msg, mock_fsm_context)

    assert await mock_fsm_context.get_state() is None
    mock_msg.answer.assert_awaited_once()
    assert "75%" in mock_msg.answer.call_args[0][0]

    alerts = get_alerts_by_account(acc_id, tmp_db_path)
    assert len(alerts) == 1
    assert alerts[0]["threshold_pct"] == 75.0


@pytest.mark.asyncio
async def test_acc_alerts_cb_unauthorized(tmp_db_path, monkeypatch):
    monkeypatch.setattr("app.config.config.DB_PATH", tmp_db_path)
    monkeypatch.setattr("app.config.config.OWNER_ID", 111)

    acc_id = add_account("SecretAcc", "tok", user_id=111, db_path=tmp_db_path)

    # User 222 has no access
    mock_cb = MagicMock(spec=CallbackQuery)
    mock_cb.data = f"alerts_{acc_id}"
    mock_cb.from_user = MagicMock()
    mock_cb.from_user.id = 222
    mock_cb.answer = AsyncMock()

    await acc_alerts_cb(mock_cb)
    mock_cb.answer.assert_awaited_with("Доступ запрещен.", show_alert=True)


@pytest.mark.asyncio
async def test_add_alert_menu_cb_unauthorized(tmp_db_path, monkeypatch):
    monkeypatch.setattr("app.config.config.DB_PATH", tmp_db_path)
    monkeypatch.setattr("app.config.config.OWNER_ID", 111)

    acc_id = add_account("SecretAcc", "tok", user_id=111, db_path=tmp_db_path)

    mock_cb = MagicMock(spec=CallbackQuery)
    mock_cb.data = f"addalert_{acc_id}"
    mock_cb.from_user = MagicMock()
    mock_cb.from_user.id = 222
    mock_cb.answer = AsyncMock()

    await add_alert_menu_cb(mock_cb)
    mock_cb.answer.assert_awaited_with("Доступ запрещен.", show_alert=True)


@pytest.mark.asyncio
async def test_add_alert_menu_cb_not_found(tmp_db_path, monkeypatch):
    monkeypatch.setattr("app.config.config.DB_PATH", tmp_db_path)
    mock_cb = MagicMock(spec=CallbackQuery)
    mock_cb.data = "addalert_9999"
    mock_cb.answer = AsyncMock()

    await add_alert_menu_cb(mock_cb)
    mock_cb.answer.assert_awaited_with("Аккаунт не найден", show_alert=True)


@pytest.mark.asyncio
async def test_custom_alert_pct_input_non_text(mock_fsm_context):
    await mock_fsm_context.set_state(CustomAlertFSM.pct)
    mock_msg = MagicMock(spec=Message)
    mock_msg.text = None
    mock_msg.answer = AsyncMock()

    await custom_alert_pct_input(mock_msg, mock_fsm_context)
    mock_msg.answer.assert_awaited_with("❌ Пожалуйста, отправьте число от 1 до 99.")


@pytest.mark.asyncio
async def test_custom_alert_pct_input_expired_state(mock_fsm_context):
    await mock_fsm_context.set_state(CustomAlertFSM.pct)
    mock_msg = MagicMock(spec=Message)
    mock_msg.text = "80"
    mock_msg.answer = AsyncMock()

    await custom_alert_pct_input(mock_msg, mock_fsm_context)
    mock_msg.answer.assert_awaited_with("❌ Сессия настройки алерта устарела. Начните заново через список аккаунтов.")
    assert await mock_fsm_context.get_state() is None


@pytest.mark.asyncio
async def test_set_alert_preset_cb_burn_rate(tmp_db_path, monkeypatch):
    monkeypatch.setattr("app.config.config.DB_PATH", tmp_db_path)
    acc_id = add_account("BurnAcc", "token", tmp_db_path)

    mock_cb = MagicMock(spec=CallbackQuery)
    mock_cb.data = f"setalt_{acc_id}_burn_3_50"
    mock_cb.message = MagicMock(spec=Message)
    mock_cb.message.edit_text = AsyncMock()
    mock_cb.answer = AsyncMock()

    await set_alert_preset_cb(mock_cb)
    mock_cb.answer.assert_any_await("Алерт успешно добавлен!")
    alerts = get_alerts_by_account(acc_id, tmp_db_path)
    assert len(alerts) == 1
    assert alerts[0]["alert_type"] == "burn_rate"


@pytest.mark.asyncio
async def test_custom_unit_choice_cb():
    mock_cb = MagicMock(spec=CallbackQuery)
    mock_cb.data = "customunit_42"
    mock_cb.message = MagicMock(spec=Message)
    mock_cb.message.edit_text = AsyncMock()
    mock_cb.answer = AsyncMock()

    await custom_unit_choice_cb(mock_cb)
    mock_cb.message.edit_text.assert_awaited_once()
    mock_cb.answer.assert_awaited_once()


