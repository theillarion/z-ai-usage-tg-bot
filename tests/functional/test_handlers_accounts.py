"""Functional tests for account management handlers."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from aiogram.types import CallbackQuery, Message

from app.database import add_account, get_accounts
from app.handlers.accounts import (
    add_acc_name,
    add_acc_start,
    add_acc_token,
    del_acc_cb,
    list_accs_cb,
    view_acc_cb,
)
from app.states import AddAccountFSM


@pytest.mark.asyncio
async def test_add_acc_start(mock_fsm_context):
    mock_cb = MagicMock(spec=CallbackQuery)
    mock_cb.message = MagicMock(spec=Message)
    mock_cb.message.answer = AsyncMock()
    mock_cb.answer = AsyncMock()

    await add_acc_start(mock_cb, mock_fsm_context)

    assert await mock_fsm_context.get_state() == AddAccountFSM.token.state
    mock_cb.message.answer.assert_awaited_once()
    assert "Пришли мне твой API ключ" in mock_cb.message.answer.call_args[0][0]
    mock_cb.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_add_acc_token_ellipsis_error(mock_fsm_context):
    mock_msg = MagicMock(spec=Message)
    mock_msg.text = "abc12345…def"
    mock_msg.answer = AsyncMock()

    await add_acc_token(mock_msg, mock_fsm_context)

    mock_msg.answer.assert_awaited_once()
    assert "многоточие" in mock_msg.answer.call_args[0][0]
    assert await mock_fsm_context.get_state() is None


@pytest.mark.asyncio
async def test_add_acc_token_valid(mock_fsm_context):
    mock_msg = MagicMock(spec=Message)
    mock_msg.text = "Bearer valid_key_999"
    progress_msg = MagicMock(spec=Message)
    progress_msg.edit_text = AsyncMock()
    mock_msg.answer = AsyncMock(return_value=progress_msg)

    with patch("app.handlers.accounts.check_token", return_value=(True, {"limits": []})):
        await add_acc_token(mock_msg, mock_fsm_context)

    progress_msg.edit_text.assert_awaited_once()
    assert "✅ Токен рабочий!" in progress_msg.edit_text.call_args[0][0]
    assert await mock_fsm_context.get_state() == AddAccountFSM.name.state
    data = await mock_fsm_context.get_data()
    assert data["token"] == "valid_key_999"


@pytest.mark.asyncio
async def test_add_acc_token_invalid(mock_fsm_context):
    mock_msg = MagicMock(spec=Message)
    mock_msg.text = "invalid_key"
    progress_msg = MagicMock(spec=Message)
    progress_msg.edit_text = AsyncMock()
    mock_msg.answer = AsyncMock(return_value=progress_msg)

    with patch("app.handlers.accounts.check_token", return_value=(False, "Unauthorized")):
        await add_acc_token(mock_msg, mock_fsm_context)

    progress_msg.edit_text.assert_awaited_once()
    assert "❌ Ошибка проверки токена" in progress_msg.edit_text.call_args[0][0]


@pytest.mark.asyncio
async def test_add_acc_name(mock_fsm_context, tmp_db_path, monkeypatch):
    monkeypatch.setattr("app.config.config.DB_PATH", tmp_db_path)
    await mock_fsm_context.update_data(token="stored_token")
    await mock_fsm_context.set_state(AddAccountFSM.name)

    mock_msg = MagicMock(spec=Message)
    mock_msg.text = "Мой Аккаунт"
    mock_msg.answer = AsyncMock()

    await add_acc_name(mock_msg, mock_fsm_context)

    assert await mock_fsm_context.get_state() is None
    mock_msg.answer.assert_awaited_once()
    assert "Мой Аккаунт" in mock_msg.answer.call_args[0][0]

    accounts = get_accounts(tmp_db_path)
    assert len(accounts) == 1
    assert accounts[0]["name"] == "Мой Аккаунт"
    assert accounts[0]["token"] == "stored_token"


@pytest.mark.asyncio
async def test_list_accs_empty(tmp_db_path, monkeypatch):
    monkeypatch.setattr("app.config.config.DB_PATH", tmp_db_path)
    mock_cb = MagicMock(spec=CallbackQuery)
    mock_cb.message = MagicMock(spec=Message)
    mock_cb.message.edit_text = AsyncMock()
    mock_cb.answer = AsyncMock()

    await list_accs_cb(mock_cb)

    mock_cb.message.edit_text.assert_awaited_once()
    assert "У вас пока нет добавленных аккаунтов" in mock_cb.message.edit_text.call_args[0][0]


@pytest.mark.asyncio
async def test_list_accs_with_items(tmp_db_path, monkeypatch):
    monkeypatch.setattr("app.config.config.DB_PATH", tmp_db_path)
    add_account("Test 1", "tok1", tmp_db_path)
    add_account("Test 2", "tok2", tmp_db_path)

    mock_cb = MagicMock(spec=CallbackQuery)
    mock_cb.message = MagicMock(spec=Message)
    mock_cb.message.edit_text = AsyncMock()
    mock_cb.answer = AsyncMock()

    await list_accs_cb(mock_cb)

    mock_cb.message.edit_text.assert_awaited_once()
    assert "Ваши аккаунты:" in mock_cb.message.edit_text.call_args[0][0]
    mock_cb.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_view_acc_cb_not_found(tmp_db_path, monkeypatch):
    monkeypatch.setattr("app.config.config.DB_PATH", tmp_db_path)
    mock_cb = MagicMock(spec=CallbackQuery)
    mock_cb.data = "view_9999"
    mock_cb.answer = AsyncMock()

    await view_acc_cb(mock_cb)

    mock_cb.answer.assert_awaited_once_with("Аккаунт не найден", show_alert=True)


@pytest.mark.asyncio
async def test_view_acc_cb_success(tmp_db_path, monkeypatch, sample_quota_data):
    monkeypatch.setattr("app.config.config.DB_PATH", tmp_db_path)
    acc_id = add_account("Main", "tok_valid", tmp_db_path)

    mock_cb = MagicMock(spec=CallbackQuery)
    mock_cb.data = f"view_{acc_id}"
    mock_cb.message = MagicMock(spec=Message)
    mock_cb.message.edit_text = AsyncMock()
    mock_cb.answer = AsyncMock()

    with patch("app.handlers.accounts.check_token", return_value=(True, sample_quota_data)):
        await view_acc_cb(mock_cb)

    # First call: requesting... Second call: formatted limits text
    assert mock_cb.message.edit_text.await_count == 2
    args, kwargs = mock_cb.message.edit_text.call_args
    assert "Main" in args[0]
    assert "GLM Coding Plan" in args[0]


@pytest.mark.asyncio
async def test_view_acc_cb_message_not_modified(tmp_db_path, monkeypatch, sample_quota_data):
    monkeypatch.setattr("app.config.config.DB_PATH", tmp_db_path)
    acc_id = add_account("Main", "tok_valid", tmp_db_path)

    mock_cb = MagicMock(spec=CallbackQuery)
    mock_cb.data = f"view_{acc_id}"
    mock_cb.message = MagicMock(spec=Message)
    # The second edit_text raises "message is not modified"
    mock_cb.message.edit_text = AsyncMock(side_effect=[None, Exception("Bad Request: message is not modified")])
    mock_cb.answer = AsyncMock()

    with patch("app.handlers.accounts.check_token", return_value=(True, sample_quota_data)):
        await view_acc_cb(mock_cb)

    mock_cb.answer.assert_awaited_with("Данные актуальны (без изменений)")


@pytest.mark.asyncio
async def test_view_acc_cb_error(tmp_db_path, monkeypatch):
    monkeypatch.setattr("app.config.config.DB_PATH", tmp_db_path)
    acc_id = add_account("Main", "tok_bad", tmp_db_path)

    mock_cb = MagicMock(spec=CallbackQuery)
    mock_cb.data = f"view_{acc_id}"
    mock_cb.message = MagicMock(spec=Message)
    mock_cb.message.edit_text = AsyncMock()
    mock_cb.answer = AsyncMock()

    with patch("app.handlers.accounts.check_token", return_value=(False, "Connection reset")):
        await view_acc_cb(mock_cb)

    assert mock_cb.message.edit_text.await_count == 2
    args, _ = mock_cb.message.edit_text.call_args
    assert "Ошибка получения лимитов" in args[0]


@pytest.mark.asyncio
async def test_view_acc_cb_unhandled_exception(tmp_db_path, monkeypatch, sample_quota_data):
    monkeypatch.setattr("app.config.config.DB_PATH", tmp_db_path)
    acc_id = add_account("Main", "tok_valid", tmp_db_path)

    mock_cb = MagicMock(spec=CallbackQuery)
    mock_cb.data = f"view_{acc_id}"
    mock_cb.message = MagicMock(spec=Message)
    mock_cb.message.edit_text = AsyncMock(side_effect=[None, RuntimeError("Fatal UI error")])
    mock_cb.answer = AsyncMock()

    with patch("app.handlers.accounts.check_token", return_value=(True, sample_quota_data)):
        with pytest.raises(RuntimeError, match="Fatal UI error"):
            await view_acc_cb(mock_cb)


@pytest.mark.asyncio
async def test_view_acc_cb_error_edit_fails_silently(tmp_db_path, monkeypatch):
    monkeypatch.setattr("app.config.config.DB_PATH", tmp_db_path)
    acc_id = add_account("Main", "tok_bad", tmp_db_path)

    mock_cb = MagicMock(spec=CallbackQuery)
    mock_cb.data = f"view_{acc_id}"
    mock_cb.message = MagicMock(spec=Message)
    # First edit succeeds (loading...), second edit fails
    mock_cb.message.edit_text = AsyncMock(side_effect=[None, Exception("Telegram connection lost")])
    mock_cb.answer = AsyncMock()

    with patch("app.handlers.accounts.check_token", return_value=(False, "Failed")):
        # Should not raise exception because it is caught in try...except
        await view_acc_cb(mock_cb)



@pytest.mark.asyncio
async def test_del_acc_cb(tmp_db_path, monkeypatch):

    monkeypatch.setattr("app.config.config.DB_PATH", tmp_db_path)
    acc_id = add_account("ToDelete", "tok", tmp_db_path)

    mock_cb = MagicMock(spec=CallbackQuery)
    mock_cb.data = f"del_{acc_id}"
    mock_cb.message = MagicMock(spec=Message)
    mock_cb.message.edit_text = AsyncMock()
    mock_cb.answer = AsyncMock()

    await del_acc_cb(mock_cb)

    assert get_accounts(tmp_db_path) == []
    mock_cb.answer.assert_awaited_with("Удалено!")
    mock_cb.message.edit_text.assert_awaited_once()
