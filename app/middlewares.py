"""Aiogram middlewares for authorization and access control."""

from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject


class AuthMiddleware(BaseMiddleware):
    """Restricts bot interactions to the configured owner only."""

    def __init__(self, owner_id: int):
        super().__init__()
        self.owner_id = owner_id

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user and user.id != self.owner_id:
            if isinstance(event, Message):
                await event.answer(
                    f'Бот отвечает только закрытому кругу лиц. Для связи пишите <a href="tg://user?id={self.owner_id}">владельцу</a>.',
                    parse_mode="HTML",
                )
            elif isinstance(event, CallbackQuery):
                await event.answer("Доступ запрещен.", show_alert=True)
            return

        return await handler(event, data)
