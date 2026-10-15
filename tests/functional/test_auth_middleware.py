"""Functional tests for AuthMiddleware with approval flow."""

from unittest.mock import AsyncMock, MagicMock
import pytest
from aiogram.types import CallbackQuery, Message, User
from app.database import get_user, init_db, upsert_user
from app.middlewares import AuthMiddleware


@pytest.mark.asyncio
async def test_auth_middleware_owner_allowed(tmp_db_path, monkeypatch):
    monkeypatch.setattr("app.config.config.DB_PATH", tmp_db_path)
    owner_id = 12345
    middleware = AuthMiddleware(owner_id=owner_id)

    mock_handler = AsyncMock(return_value="handler_result")
    mock_event = MagicMock()
    mock_user = MagicMock(spec=User)
    mock_user.id = owner_id
    mock_user.username = "owner"
    mock_user.first_name = "Owner"

    data = {"event_from_user": mock_user}
    result = await middleware(mock_handler, mock_event, data)

    assert result == "handler_result"
    mock_handler.assert_awaited_once_with(mock_event, data)
    db_owner = get_user(owner_id, tmp_db_path)
    assert db_owner["is_approved"] is True
    assert db_owner["is_admin"] is True


@pytest.mark.asyncio
async def test_auth_middleware_approved_user_allowed(tmp_db_path, monkeypatch):
    monkeypatch.setattr("app.config.config.DB_PATH", tmp_db_path)
    owner_id = 12345
    user_id = 55555
    upsert_user(user_id, "approved_user", "User", is_approved=1, db_path=tmp_db_path)

    middleware = AuthMiddleware(owner_id=owner_id)
    mock_handler = AsyncMock(return_value="ok")
    mock_event = MagicMock()
    mock_user = MagicMock(spec=User)
    mock_user.id = user_id

    data = {"event_from_user": mock_user}
    result = await middleware(mock_handler, mock_event, data)
    assert result == "ok"
    mock_handler.assert_awaited_once()


@pytest.mark.asyncio
async def test_auth_middleware_new_user_registered_as_pending(tmp_db_path, monkeypatch, mock_bot):
    monkeypatch.setattr("app.config.config.DB_PATH", tmp_db_path)
    owner_id = 12345
    new_user_id = 99999

    middleware = AuthMiddleware(owner_id=owner_id)
    mock_handler = AsyncMock()
    mock_msg = MagicMock(spec=Message)
    mock_msg.answer = AsyncMock()

    mock_user = MagicMock(spec=User)
    mock_user.id = new_user_id
    mock_user.username = "stranger"
    mock_user.first_name = "Newbie"

    data = {"event_from_user": mock_user, "bot": mock_bot}
    result = await middleware(mock_handler, mock_msg, data)

    assert result is None
    mock_handler.assert_not_awaited()
    # User informed
    mock_msg.answer.assert_awaited_once()
    assert "находится на рассмотрении" in mock_msg.answer.call_args[0][0]

    # Owner notified
    mock_bot.send_message.assert_awaited_once()
    assert "@stranger" in mock_bot.send_message.call_args[0][1]

    # Stored in DB as pending
    db_user = get_user(new_user_id, tmp_db_path)
    assert db_user is not None
    assert db_user["is_approved"] is False


@pytest.mark.asyncio
async def test_auth_middleware_rejected_callback_blocked(tmp_db_path, monkeypatch):
    monkeypatch.setattr("app.config.config.DB_PATH", tmp_db_path)
    owner_id = 12345
    blocked_id = 88888
    upsert_user(blocked_id, "blocked", "Blocked", is_approved=0, db_path=tmp_db_path)

    middleware = AuthMiddleware(owner_id=owner_id)
    mock_handler = AsyncMock()
    mock_cb = MagicMock(spec=CallbackQuery)
    mock_cb.answer = AsyncMock()

    mock_user = MagicMock(spec=User)
    mock_user.id = blocked_id

    data = {"event_from_user": mock_user}
    result = await middleware(mock_handler, mock_cb, data)

    assert result is None
    mock_handler.assert_not_awaited()
    mock_cb.answer.assert_awaited_once_with("Доступ ограничен. Заявка на рассмотрении.", show_alert=True)


@pytest.mark.asyncio
async def test_auth_middleware_no_user():
    middleware = AuthMiddleware(owner_id=12345)
    mock_handler = AsyncMock(return_value="no_user_ok")
    mock_event = MagicMock()
    data = {}

    result = await middleware(mock_handler, mock_event, data)
    assert result == "no_user_ok"
    mock_handler.assert_awaited_once_with(mock_event, data)
