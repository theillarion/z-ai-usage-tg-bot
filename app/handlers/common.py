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
    """Cancel current FSM state and return to main menu."""
    await state.clear()
    from_user = getattr(message, "from_user", None)
    user_id = getattr(from_user, "id", 0) if from_user else 0
    is_admin = bool(config.OWNER_ID and user_id == config.OWNER_ID)
    await message.answer(
        "Действие отменено.",
        reply_markup=get_main_menu_kb(is_admin=is_admin),
    )


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
    try:
        await callback.message.edit_text(
            f"🤖 <b>О проекте:</b> \nБот для мониторинга лимитов Z.ai.\n\n"
            f"👨‍💻 <b>Владелец:</b> <a href='tg://user?id={config.OWNER_ID}'>@theillarion</a>\n"
            f"🐙 <b>Исходный код:</b> <a href='{config.REPO_URL}'>GitHub Repository</a>\n\n"
            f"🏷 <b>Версия:</b> {config.VERSION}",
            reply_markup=get_author_info_kb(),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    except Exception:
        pass
    try:
        await callback.answer()
    except Exception:
        pass


@router.callback_query(F.data == "start_menu")
async def start_menu_cb(callback: CallbackQuery):
    """Return to main menu from inline button preserving user context and admin rights."""
    from_user = getattr(callback, "from_user", None)
    user_id = getattr(from_user, "id", 0) if from_user else 0
    is_admin = bool(config.OWNER_ID and user_id == config.OWNER_ID)
    text = "Привет! Я приватный бот для мониторинга лимитов Z.ai.\nЧто будем делать?"
    kb = get_main_menu_kb(is_admin=is_admin)
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)
    try:
        await callback.answer()
    except Exception:
        pass

