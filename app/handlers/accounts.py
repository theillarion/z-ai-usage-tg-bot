"""Account management handlers: add, view, list, delete with token security and permission checks."""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import config
from app.database import (
    add_account,
    check_account_access,
    delete_account,
    get_account_by_id,
    get_accounts,
)
from app.formatters import format_limits_text
from app.keyboards import (
    get_account_added_kb,
    get_account_view_kb,
    get_accounts_list_kb,
    get_empty_accounts_kb,
)
from app.states import AddAccountFSM
from app.zai_client import check_token

router = Router(name="accounts")


@router.callback_query(F.data == "add_acc")
async def add_acc_start(callback: CallbackQuery, state: FSMContext):
    """Start account addition flow by prompting for API token."""
    await callback.message.answer(
        "Пришли мне твой API ключ (Bearer token) от Z.ai.\n\n"
        "💡 <i>Подсказка: ты можешь сгенерировать постоянный API-ключ на странице "
        "https://z.ai/manage-apikey</i>\n\n"
        "🔒 <i>В целях безопасности ваше сообщение с ключом будет удалено сразу после обработки.</i>",
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    await state.set_state(AddAccountFSM.token)
    await callback.answer()


@router.message(AddAccountFSM.token)
async def add_acc_token(message: Message, state: FSMContext):
    """Validate submitted token, clean up message for privacy, and proceed to naming."""
    token = message.text.strip()

    # Security: Delete message containing sensitive Bearer token from chat history
    try:
        await message.delete()
    except Exception:
        pass

    if "…" in token or "\u2026" in token:
        await message.answer("❌ Ошибка: В токене есть многоточие. Скопируй ключ целиком!")
        return

    token = token.encode("ascii", "ignore").decode("ascii")

    if token.startswith("Bearer "):
        token = token[7:]

    msg = await message.answer("🔄 Проверяю токен...")
    ok, data_or_err = check_token(token)

    if ok:
        await state.update_data(token=token)
        await msg.edit_text("✅ Токен рабочий!\nКак назовем этот аккаунт? (например, 'Основной')")
        await state.set_state(AddAccountFSM.name)
    else:
        await msg.edit_text(
            f"❌ Ошибка проверки токена:\n{data_or_err}\n\n"
            f"Попробуй прислать другой токен или /cancel для отмены."
        )


@router.message(AddAccountFSM.name)
async def add_acc_name(message: Message, state: FSMContext):
    """Save the named account associated with user_id."""
    name = message.text.strip()
    data = await state.get_data()
    token = data["token"]

    from_user = getattr(message, "from_user", None)
    user_id = getattr(from_user, "id", config.OWNER_ID) if from_user else config.OWNER_ID
    add_account(name, token, user_id=user_id)
    await state.clear()

    await message.answer(
        f"🎉 Аккаунт '{name}' успешно добавлен!",
        reply_markup=get_account_added_kb(),
    )


@router.callback_query(F.data == "list_accs")
async def list_accs_cb(callback: CallbackQuery):
    """List accessible accounts (owned + shared) or display empty state."""
    from_user = getattr(callback, "from_user", None)
    user_id = getattr(from_user, "id", None) if from_user else None
    accs = get_accounts(user_id=user_id)
    if not accs:
        await callback.message.edit_text(
            "У вас пока нет добавленных аккаунтов.",
            reply_markup=get_empty_accounts_kb(),
        )
        return

    await callback.message.edit_text(
        "Ваши аккаунты:",
        reply_markup=get_accounts_list_kb(accs),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("view_"))
async def view_acc_cb(callback: CallbackQuery):
    """View quota and subscription details for a specific account with access verification."""
    acc_id = int(callback.data.split("_")[1])
    from_user = getattr(callback, "from_user", None)
    user_id = getattr(from_user, "id", config.OWNER_ID) if from_user else config.OWNER_ID

    acc = get_account_by_id(acc_id)
    if not acc:
        await callback.answer("Аккаунт не найден", show_alert=True)
        return

    has_access, is_owner = check_account_access(acc_id, user_id)
    if not has_access:
        await callback.answer("Доступ запрещен.", show_alert=True)
        return


    await callback.message.edit_text(f"🔄 Запрашиваю лимиты для '{acc['name']}'...")

    ok, data = check_token(acc["token"])
    is_admin = bool(config.OWNER_ID and user_id == config.OWNER_ID)
    kb = get_account_view_kb(acc_id, is_owner=is_owner, is_admin=is_admin)

    if ok:
        text = format_limits_text(acc["name"], data)
        try:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except Exception as e:
            if "message is not modified" in str(e).lower():
                await callback.answer("Данные актуальны (без изменений)")
            else:
                raise e
    else:
        try:
            await callback.message.edit_text(
                f"❌ Ошибка получения лимитов для '{acc['name']}':\n{data}",
                reply_markup=kb,
            )
        except Exception:
            pass


@router.callback_query(F.data.startswith("del_"))
async def del_acc_cb(callback: CallbackQuery):
    """Delete an account after validating owner or admin privileges."""
    acc_id = int(callback.data.split("_")[1])
    from_user = getattr(callback, "from_user", None)
    user_id = getattr(from_user, "id", config.OWNER_ID) if from_user else config.OWNER_ID

    has_access, is_owner = check_account_access(acc_id, user_id)
    is_admin = bool(config.OWNER_ID and user_id == config.OWNER_ID)

    if not (is_owner or is_admin):
        await callback.answer("У вас нет прав на удаление этого аккаунта", show_alert=True)
        return

    delete_account(acc_id)
    await callback.answer("Удалено!")
    await list_accs_cb(callback)

