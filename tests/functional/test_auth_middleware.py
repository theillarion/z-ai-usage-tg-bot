"""Functional tests for AuthMiddleware."""

from unittest.mock import AsyncMock, MagicMock
import pytest
from aiogram.types import CallbackQuery, Message, User
from app.middlewares import AuthMiddleware


@pytest.mark.asyncio
async def test_auth_middleware_owner_allowed():
    owner_id = 12345
    middleware = AuthMiddleware(owner_id=owner_id)

    mock_handler = AsyncMock(return_value="handler_result")
    mock_event = MagicMock()
    mock_user = MagicMock(spec=User)
    mock_user.id = owner_id

    data = {"event_from_user": mock_user}
    result = await middleware(mock_handler, mock_event, data)

    assert result == "handler_result"
    mock_handler.assert_awaited_once_with(mock_event, data)


@pytest.mark.asyncio
async def test_auth_middleware_non_owner_message_blocked():
    owner_id = 12345
    middleware = AuthMiddleware(owner_id=owner_id)

    mock_handler = AsyncMock()
    mock_msg = MagicMock(spec=Message)
    mock_msg.answer = AsyncMock()

    mock_user = MagicMock(spec=User)
    mock_user.id = 99999  # Stranger

    data = {"event_from_user": mock_user}
    result = await middleware(mock_handler, mock_msg, data)

    assert result is None
    mock_handler.assert_not_awaited()
    mock_msg.answer.assert_awaited_once()
    assert "закрытому кругу лиц" in mock_msg.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_auth_middleware_non_owner_callback_blocked():
    owner_id = 12345
    middleware = AuthMiddleware(owner_id=owner_id)

    mock_handler = AsyncMock()
    mock_cb = MagicMock(spec=CallbackQuery)
    mock_cb.answer = AsyncMock()

    mock_user = MagicMock(spec=User)
    mock_user.id = 99999  # Stranger

    data = {"event_from_user": mock_user}
    result = await middleware(mock_handler, mock_cb, data)

    assert result is None
    mock_handler.assert_not_awaited()
    mock_cb.answer.assert_awaited_once_with("Доступ запрещен.", show_alert=True)


@pytest.mark.asyncio
async def test_auth_middleware_no_user():
    owner_id = 12345
    middleware = AuthMiddleware(owner_id=owner_id)

    mock_handler = AsyncMock(return_value="ok")
    mock_event = MagicMock()
    data = {}

    result = await middleware(mock_handler, mock_event, data)
    assert result == "ok"
    mock_handler.assert_awaited_once_with(mock_event, data)
