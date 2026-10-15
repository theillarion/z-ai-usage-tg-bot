"""Aiogram middlewares for authorization and access control."""

from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware, Bot
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, TelegramObject

from app.database import get_user, upsert_user


class AuthMiddleware(BaseMiddleware):
    """Enforces user approval and admin authorization."""

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
        if not user:
            return await handler(event, data)

        # 1. Owner always has full admin access
        if user.id == self.owner_id:
            upsert_user(
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                is_approved=1,
                is_admin=1,
            )
            return await handler(event, data)

        # 2. Check if user is registered and approved
        db_user = get_user(user.id)
        if db_user and db_user["is_approved"]:
            return await handler(event, data)

        # 3. New user requesting access
        if db_user is None:
            upsert_user(
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                is_approved=0,
                is_admin=0,
            )
            # Notify owner
            bot: Bot = data.get("bot")
            if bot and self.owner_id:
                uname = f"@{user.username}" if user.username else "без username"
                text = (
                    f"🔔 <b>Новый запрос на доступ к боту!</b>\n\n"
                    f"👤 <b>Пользователь:</b> {user.first_name or 'Имя не указано'} ({uname})\n"
                    f"🆔 <code>{user.id}</code>\n"
                )
                kb = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"adm_appr_{user.id}"),
                            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"adm_rejc_{user.id}"),
                        ]
                    ]
                )
                try:
                    await bot.send_message(self.owner_id, text, reply_markup=kb, parse_mode="HTML")
                except Exception:
                    pass

        # 4. Inform unapproved user
        if isinstance(event, Message):
            await event.answer(
                f"⏳ <b>Доступ ограничен.</b>\n"
                f"Ваша заявка находится на рассмотрении у администратора. "
                f"Для связи пишите <a href='tg://user?id={self.owner_id}'>владельцу</a>.",
                parse_mode="HTML",
            )
        elif isinstance(event, CallbackQuery):
            await event.answer("Доступ ограничен. Заявка на рассмотрении.", show_alert=True)

        return
