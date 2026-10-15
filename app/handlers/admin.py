"""Admin panel and account sharing handlers."""

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery

from app.config import config
from app.database import (
    check_account_access,
    get_account_by_id,
    get_accounts,
    get_all_users,
    get_shared_users_for_account,
    get_user,
    set_user_approval,
    share_account,
    unshare_account,
)
from app.keyboards import (
    get_account_shares_management_kb,
    get_admin_menu_kb,
    get_admin_user_detail_kb,
    get_admin_users_kb,
    get_pick_user_to_share_kb,
    get_share_accounts_list_kb,
)

router = Router(name="admin")


def _is_admin(user_id: int) -> bool:
    if config.OWNER_ID and user_id == config.OWNER_ID:
        return True
    u = get_user(user_id)
    return bool(u and u.get("is_admin"))


@router.callback_query(F.data == "admin_menu")
async def admin_menu_cb(callback: CallbackQuery):
    """Render main admin panel menu."""
    if not _is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен.", show_alert=True)
        return

    text = (
        "👑 <b>Панель администратора</b>\n\n"
        "Здесь вы можете управлять доступом пользователей к боту "
        "и распределять права на просмотр информации по токенам."
    )
    await callback.message.edit_text(text, reply_markup=get_admin_menu_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_users")
async def admin_users_cb(callback: CallbackQuery):
    """List all users for admin review."""
    if not _is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен.", show_alert=True)
        return

    users = get_all_users()
    text = (
        "👥 <b>Управление пользователями</b>\n\n"
        "✅ — Доступ разрешен\n"
        "⏳ — Ожидает одобрения\n\n"
        "Выберите пользователя для настройки:"
    )
    await callback.message.edit_text(text, reply_markup=get_admin_users_kb(users), parse_mode="HTML")
    await callback.answer()


async def _render_user_card(callback: CallbackQuery, target: Dict[str, Any]):
    """Render or update user details card."""
    target_id = target["user_id"]
    is_approved = target["is_approved"]
    status_str = "✅ Одобрен" if is_approved else "⏳ Ожидает одобрения / Отклонён"
    uname_str = f"@{target['username']}" if target.get("username") else "нет"
    text = (
        f"👤 <b>Пользователь:</b> {target.get('first_name') or 'Без имени'}\n"
        f"🆔 <b>ID:</b> <code>{target_id}</code>\n"
        f"💬 <b>Username:</b> {uname_str}\n"
        f"📊 <b>Статус:</b> {status_str}\n"
    )
    kb = get_admin_user_detail_kb(target_id, is_approved)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("adm_usr_"))
async def admin_user_detail_cb(callback: CallbackQuery):
    """Show details for selected user with toggle button."""
    if not _is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен.", show_alert=True)
        return

    target_id = int(callback.data.split("_")[2])
    target = get_user(target_id)
    if not target:
        await callback.answer("Пользователь не найден", show_alert=True)
        return

    await _render_user_card(callback, target)
    try:
        await callback.answer()
    except Exception:
        pass


@router.callback_query(F.data.startswith("adm_appr_"))
async def admin_approve_cb(callback: CallbackQuery, bot: Bot):
    """Approve a user's access request."""
    if not _is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен.", show_alert=True)
        return

    target_id = int(callback.data.split("_")[2])
    target = get_user(target_id)
    if not target:
        await callback.answer("Пользователь не найден", show_alert=True)
        return

    # Anti-spam / idempotency: do not notify again if already approved
    if target["is_approved"]:
        await callback.answer("Пользователь уже одобрен.")
        await _render_user_card(callback, target)
        return

    set_user_approval(target_id, 1)

    try:
        await bot.send_message(
            target_id,
            "🎉 <b>Ваша заявка одобрена!</b>\nТеперь вам доступен функционал бота. Отправьте /start для начала работы.",
            parse_mode="HTML",
        )
    except Exception:
        pass

    await callback.answer("Доступ одобрен!")
    target["is_approved"] = True
    await _render_user_card(callback, target)


@router.callback_query(F.data.startswith("adm_rejc_"))
async def admin_reject_cb(callback: CallbackQuery, bot: Bot):
    """Revoke or reject a user's access."""
    if not _is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен.", show_alert=True)
        return

    target_id = int(callback.data.split("_")[2])
    target = get_user(target_id)
    if not target:
        await callback.answer("Пользователь не найден", show_alert=True)
        return

    # Anti-spam / idempotency: do not notify again if already revoked/unapproved
    if not target["is_approved"]:
        await callback.answer("Доступ пользователя уже закрыт.")
        await _render_user_card(callback, target)
        return

    set_user_approval(target_id, 0)

    try:
        await bot.send_message(
            target_id,
            "🚫 Доступ к боту был отозван администратором.",
            parse_mode="HTML",
        )
    except Exception:
        pass

    await callback.answer("Доступ отозван!")
    target["is_approved"] = False
    await _render_user_card(callback, target)



@router.callback_query(F.data == "admin_shares")
async def admin_shares_cb(callback: CallbackQuery):
    """List all accounts for token access management."""
    if not _is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен.", show_alert=True)
        return

    accounts = get_accounts(None)
    text = (
        "🔑 <b>Управление доступом к токенам</b>\n\n"
        "Выберите аккаунт, чтобы настроить, какие пользователи "
        "могут просматривать его лимиты и настраивать свои алерты:\n\n"
        "🔒 <i>Сами Bearer-токены остаются строго скрытыми.</i>"
    )
    await callback.message.edit_text(text, reply_markup=get_share_accounts_list_kb(accounts), parse_mode="HTML")
    await callback.answer()


async def _render_account_shares(callback: CallbackQuery, acc_id: int):
    """View and manage users who have access to this account."""
    user_id = callback.from_user.id

    has_access, is_owner = check_account_access(acc_id, user_id)
    if not (is_owner or _is_admin(user_id)):
        await callback.answer("У вас нет прав на управление доступом к этому аккаунту", show_alert=True)
        return

    acc = get_account_by_id(acc_id)
    if not acc:
        await callback.answer("Аккаунт не найден", show_alert=True)
        return

    shared_users = get_shared_users_for_account(acc_id)
    all_users = get_all_users()
    shared_uids = {u["user_id"] for u in shared_users} | {acc["user_id"]}
    available_users = [u for u in all_users if u["user_id"] not in shared_uids and u["is_approved"]]

    text = (
        f"🔑 <b>Управление доступом:</b> {acc['name']}\n\n"
        f"Пользователи с доступом видят остаток квот и могут ставить персональные алерты. "
        f"Сам ключ API им недоступен.\n\n"
    )
    if shared_users:
        text += "<b>Пользователи с доступом:</b>\n"
        for u in shared_users:
            name = u.get("username") or u.get("first_name") or str(u["user_id"])
            text += f"• {name} (ID: <code>{u['user_id']}</code>)\n"
    else:
        text += "<i>Сейчас к этому аккаунту ни у кого нет доступа, кроме владельца.</i>\n"

    kb = get_account_shares_management_kb(acc_id, shared_users, bool(available_users))
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    try:
        await callback.answer()
    except Exception:
        pass


@router.callback_query(F.data.startswith("accshare_"))
async def account_share_manage_cb(callback: CallbackQuery):
    """View and manage users who have access to this account."""
    acc_id = int(callback.data.split("_")[1])
    await _render_account_shares(callback, acc_id)


@router.callback_query(F.data.startswith("sharepick_"))
async def share_pick_user_cb(callback: CallbackQuery):
    """Pick an approved user to grant access to account."""
    acc_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id

    has_access, is_owner = check_account_access(acc_id, user_id)
    if not (is_owner or _is_admin(user_id)):
        await callback.answer("У вас нет прав", show_alert=True)
        return

    acc = get_account_by_id(acc_id)
    if not acc:
        await callback.answer("Аккаунт не найден", show_alert=True)
        return

    shared_users = get_shared_users_for_account(acc_id)
    shared_uids = {u["user_id"] for u in shared_users} | {acc["user_id"]}
    all_users = get_all_users()
    available_users = [u for u in all_users if u["user_id"] not in shared_uids and u["is_approved"]]

    if not available_users:
        await callback.answer("Нет доступных пользователей для добавления", show_alert=True)
        return

    text = f"Кому выдать доступ к информации об аккаунте <b>{acc['name']}</b>?"
    kb = get_pick_user_to_share_kb(acc_id, available_users)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("doshare_"))
async def do_share_account_cb(callback: CallbackQuery, bot: Bot):
    """Grant account access to selected user."""
    parts = callback.data.split("_")
    acc_id = int(parts[1])
    target_uid = int(parts[2])
    user_id = callback.from_user.id

    has_access, is_owner = check_account_access(acc_id, user_id)
    if not (is_owner or _is_admin(user_id)):
        await callback.answer("У вас нет прав", show_alert=True)
        return

    acc = get_account_by_id(acc_id)
    if not acc:
        await callback.answer("Аккаунт не найден", show_alert=True)
        return

    share_account(acc_id, target_uid)

    try:
        await bot.send_message(
            target_uid,
            f"🔑 Вам открыт доступ к просмотру лимитов аккаунта <b>'{acc['name']}'</b>!\n"
            f"Вы можете проверить его через команду /start в разделе «📋 Мои аккаунты».",
            parse_mode="HTML",
        )
    except Exception:
        pass

    await callback.answer("Доступ успешно выдан!")
    await _render_account_shares(callback, acc_id)


@router.callback_query(F.data.startswith("unshare_"))
async def unshare_account_cb(callback: CallbackQuery, bot: Bot):
    """Revoke account access from selected user."""
    parts = callback.data.split("_")
    acc_id = int(parts[1])
    target_uid = int(parts[2])
    user_id = callback.from_user.id

    has_access, is_owner = check_account_access(acc_id, user_id)
    if not (is_owner or _is_admin(user_id)):
        await callback.answer("У вас нет прав", show_alert=True)
        return

    acc = get_account_by_id(acc_id)
    if not acc:
        await callback.answer("Аккаунт не найден", show_alert=True)
        return

    unshare_account(acc_id, target_uid)

    try:
        await bot.send_message(
            target_uid,
            f"🚫 Доступ к аккаунту <b>'{acc['name']}'</b> был закрыт владельцем.",
            parse_mode="HTML",
        )
    except Exception:
        pass

    await callback.answer("Доступ отозван!")
    await _render_account_shares(callback, acc_id)

