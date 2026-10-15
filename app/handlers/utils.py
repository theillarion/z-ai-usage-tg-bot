"""Helper utilities for Telegram handlers."""

from aiogram.types import CallbackQuery, Message


async def safe_answer(callback: CallbackQuery, *args, **kwargs) -> None:
    """Safely answer callback query ignoring stale/duplicate errors."""
    try:
        await callback.answer(*args, **kwargs)
    except Exception:
        pass


async def safe_edit_text(message: Message, *args, **kwargs):
    """Safely edit message ignoring message-not-modified and stale errors."""
    try:
        return await message.edit_text(*args, **kwargs)
    except Exception:
        return None
