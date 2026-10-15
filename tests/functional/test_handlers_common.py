"""Functional tests for common handlers (/start, /cancel, author_info, start_menu)."""

from unittest.mock import AsyncMock, MagicMock
import pytest
from aiogram.types import CallbackQuery, Message
from app.handlers.common import author_info_cb, cancel_cmd, start_cmd, start_menu_cb
from app.states import AddAccountFSM


@pytest.mark.asyncio
async def test_cancel_cmd(mock_fsm_context):
    await mock_fsm_context.set_state(AddAccountFSM.token)
    assert await mock_fsm_context.get_state() == AddAccountFSM.token.state

    mock_msg = MagicMock(spec=Message)
    mock_msg.from_user = MagicMock(id=123)
    mock_msg.answer = AsyncMock()

    await cancel_cmd(mock_msg, mock_fsm_context)

    assert await mock_fsm_context.get_state() is None
    mock_msg.answer.assert_awaited_once()
    args, kwargs = mock_msg.answer.call_args
    assert "Действие отменено." in args[0]
    assert "reply_markup" in kwargs


@pytest.mark.asyncio
async def test_start_cmd():
    mock_msg = MagicMock(spec=Message)
    mock_msg.answer = AsyncMock()

    await start_cmd(mock_msg)

    mock_msg.answer.assert_awaited_once()
    args, kwargs = mock_msg.answer.call_args
    assert "Привет! Я приватный бот" in args[0]
    assert "reply_markup" in kwargs


@pytest.mark.asyncio
async def test_author_info_cb():
    mock_cb = MagicMock(spec=CallbackQuery)
    mock_cb.message = MagicMock(spec=Message)
    mock_cb.message.edit_text = AsyncMock()
    mock_cb.answer = AsyncMock()

    await author_info_cb(mock_cb)

    mock_cb.message.edit_text.assert_awaited_once()
    args, kwargs = mock_cb.message.edit_text.call_args
    assert "О проекте" in args[0]
    assert "Владелец" in args[0]
    assert "Исходный код" in args[0]
    mock_cb.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_start_menu_cb():
    mock_cb = MagicMock(spec=CallbackQuery)
    mock_cb.from_user = MagicMock(id=123)
    mock_cb.message = MagicMock(spec=Message)
    mock_cb.message.edit_text = AsyncMock()
    mock_cb.message.answer = AsyncMock()
    mock_cb.answer = AsyncMock()

    await start_menu_cb(mock_cb)

    mock_cb.message.edit_text.assert_awaited_once()
    mock_cb.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_author_info_cb_exception():
    mock_cb = MagicMock(spec=CallbackQuery)
    mock_cb.message = MagicMock(spec=Message)
    mock_cb.message.edit_text = AsyncMock(side_effect=RuntimeError("Edit failed"))
    mock_cb.answer = AsyncMock(side_effect=RuntimeError("Answer failed"))

    await author_info_cb(mock_cb)


@pytest.mark.asyncio
async def test_start_menu_cb_fallback():
    mock_cb = MagicMock(spec=CallbackQuery)
    mock_cb.from_user = MagicMock(id=123)
    mock_cb.message = MagicMock(spec=Message)
    mock_cb.message.edit_text = AsyncMock(side_effect=RuntimeError("Cannot edit"))
    mock_cb.message.answer = AsyncMock()
    mock_cb.answer = AsyncMock(side_effect=RuntimeError("Cannot answer"))

    await start_menu_cb(mock_cb)
    mock_cb.message.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_safe_helpers():
    from app.handlers import safe_answer, safe_edit_text

    mock_cb = MagicMock(spec=CallbackQuery)
    mock_cb.answer = AsyncMock()
    mock_msg = MagicMock(spec=Message)
    mock_msg.edit_text = AsyncMock()

    # Normal success
    await safe_answer(mock_cb, "ok")
    mock_cb.answer.assert_awaited_once_with("ok")

    await safe_edit_text(mock_msg, "new text")
    mock_msg.edit_text.assert_awaited_once_with("new text")

    # Exceptions caught safely
    mock_cb.answer.side_effect = RuntimeError("Stale query")
    await safe_answer(mock_cb, "error")

    mock_msg.edit_text.side_effect = RuntimeError("Cannot edit")
    res = await safe_edit_text(mock_msg, "error")
    assert res is None


