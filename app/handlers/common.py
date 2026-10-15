"""Common bot handlers: /start, /cancel, and author/project info."""

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import config
from app.keyboards import get_author_info_kb, get_main_menu_kb

router = Router(name="common")


@router.message(Command("cancel"))
async def cancel_cmd(message: Message, state: FSMContext):
    """Cancel current FSM state."""
    await state.clear()
    await message.answer("Действие отменено.")


@router.message(CommandStart())
async def start_cmd(message: Message):
    """Handle /start command and render main menu."""
    from_user = getattr(message, "from_user", None)
    user_id = getattr(from_user, "id", 0) if from_user else 0
    is_admin = bool(config.OWNER_ID and user_id == config.OWNER_ID)
    await message.answer(
        "Привет! Я приватный бот для мониторинга лимитов Z.ai.\nЧто будем делать?",
        reply_markup=get_main_menu_kb(is_admin=is_admin),
    )




@router.callback_query(F.data == "author_info")
async def author_info_cb(callback: CallbackQuery):
    """Display project and author information."""
    await callback.message.edit_text(
        f"🤖 <b>О проекте:</b> \nБот для мониторинга лимитов Z.ai.\n\n"
        f"👨‍💻 <b>Владелец:</b> <a href='tg://user?id={config.OWNER_ID}'>@theillarion</a>\n"
        f"🐙 <b>Исходный код:</b> <a href='{config.REPO_URL}'>GitHub Repository</a>\n\n"
        f"🏷 <b>Версия:</b> {config.VERSION}",
        reply_markup=get_author_info_kb(),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    await callback.answer()


@router.callback_query(F.data == "start_menu")
async def start_menu_cb(callback: CallbackQuery):
    """Return to main menu from inline button."""
    await start_cmd(callback.message)
    await callback.answer()
