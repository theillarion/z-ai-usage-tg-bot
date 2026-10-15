"""Inline keyboard builders for bot navigation, admin panel, and permissions."""

from typing import Any, Dict, List
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_menu_kb(is_admin: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="➕ Добавить аккаунт", callback_data="add_acc")],
        [InlineKeyboardButton(text="📋 Мои аккаунты", callback_data="list_accs")],
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton(text="👑 Админ-панель", callback_data="admin_menu")])
    buttons.append([InlineKeyboardButton(text="ℹ️ О проекте", callback_data="author_info")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_author_info_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="start_menu")]
        ]
    )


def get_empty_accounts_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить", callback_data="add_acc")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="start_menu")],
        ]
    )


def get_accounts_list_kb(accs: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    kb: List[List[InlineKeyboardButton]] = []
    for acc in accs:
        prefix = "👥 " if acc.get("is_shared") else "📊 "
        kb.append([InlineKeyboardButton(text=f"{prefix}{acc['name']}", callback_data=f"view_{acc['id']}")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="start_menu")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_account_view_kb(
    acc_id: int, is_owner: bool = True, is_admin: bool = False
) -> InlineKeyboardMarkup:
    row1 = [
        InlineKeyboardButton(text="🔄 Обновить", callback_data=f"view_{acc_id}"),
        InlineKeyboardButton(text="🔔 Алерты", callback_data=f"alerts_{acc_id}"),
    ]
    if is_owner or is_admin:
        row1.append(InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del_{acc_id}"))

    row2: List[InlineKeyboardButton] = []
    if is_owner or is_admin:
        row2.append(InlineKeyboardButton(text="🔑 Доступ", callback_data=f"accshare_{acc_id}"))
    row2.append(InlineKeyboardButton(text="🔙 К списку", callback_data="list_accs"))

    return InlineKeyboardMarkup(inline_keyboard=[row1, row2])


def get_alerts_list_kb(acc_id: int, alerts: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    kb: List[List[InlineKeyboardButton]] = []
    for a in alerts:
        unit_str = "5ч" if a["limit_unit"] == 3 else "Нед"
        pct = a["threshold_pct"]
        pct_val = int(pct) if isinstance(pct, (int, float)) and float(pct).is_integer() else pct
        lbl = (
            f"❌ Удалить: {unit_str} > {pct_val}%"
            if a["alert_type"] == "threshold"
            else f"❌ Удалить: {unit_str} BurnRate"
        )
        kb.append([InlineKeyboardButton(text=lbl, callback_data=f"delalert_{a['id']}_{acc_id}")])

    kb.append([InlineKeyboardButton(text="➕ Добавить алерт", callback_data=f"addalert_{acc_id}")])
    kb.append([InlineKeyboardButton(text="🔙 Назад к аккаунту", callback_data=f"view_{acc_id}")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_add_alert_menu_kb(acc_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏳ 5-часовой > 50%", callback_data=f"setalt_{acc_id}_threshold_3_50")],
            [InlineKeyboardButton(text="⏳ 5-часовой > 80%", callback_data=f"setalt_{acc_id}_threshold_3_80")],
            [InlineKeyboardButton(text="📅 Недельный > 50%", callback_data=f"setalt_{acc_id}_threshold_6_50")],
            [InlineKeyboardButton(text="📅 Недельный > 80%", callback_data=f"setalt_{acc_id}_threshold_6_80")],
            [InlineKeyboardButton(text="⚡️ 5ч Burn Rate (>50% за 2.5ч)", callback_data=f"setalt_{acc_id}_burn_3_50")],
            [InlineKeyboardButton(text="⚡️ Неделя Burn Rate (>50% за 2.5д)", callback_data=f"setalt_{acc_id}_burn_6_50")],
            [InlineKeyboardButton(text="✏️ Свой процент...", callback_data=f"customunit_{acc_id}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data=f"alerts_{acc_id}")],
        ]
    )


def get_custom_unit_choice_kb(acc_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏳ 5-часовой лимит", callback_data=f"customchoose_{acc_id}_3")],
            [InlineKeyboardButton(text="📅 Недельный лимит", callback_data=f"customchoose_{acc_id}_6")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data=f"addalert_{acc_id}")],
        ]
    )


def get_alert_saved_kb(acc_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔔 К списку алертов", callback_data=f"alerts_{acc_id}")],
            [InlineKeyboardButton(text="Главное меню", callback_data="start_menu")],
        ]
    )


def get_account_added_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Главное меню", callback_data="start_menu")]
        ]
    )


# --- Admin Panel Keyboards ---


def get_admin_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
            [InlineKeyboardButton(text="🔑 Управление доступом к токенам", callback_data="admin_shares")],
            [InlineKeyboardButton(text="🔙 В главное меню", callback_data="start_menu")],
        ]
    )


def get_admin_users_kb(users: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    kb: List[List[InlineKeyboardButton]] = []
    for u in users:
        icon = "✅" if u.get("is_approved") else "⏳"
        name = u.get("username") or u.get("first_name") or str(u["user_id"])
        kb.append([InlineKeyboardButton(text=f"{icon} {name}", callback_data=f"adm_usr_{u['user_id']}")])
    kb.append([InlineKeyboardButton(text="🔙 В админку", callback_data="admin_menu")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_admin_user_detail_kb(target_user_id: int, is_approved: bool) -> InlineKeyboardMarkup:
    toggle_btn = (
        InlineKeyboardButton(text="🚫 Отозвать доступ", callback_data=f"adm_rejc_{target_user_id}")
        if is_approved
        else InlineKeyboardButton(text="✅ Одобрить доступ", callback_data=f"adm_appr_{target_user_id}")
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [toggle_btn],
            [InlineKeyboardButton(text="🔙 К списку пользователей", callback_data="admin_users")],
        ]
    )


def get_share_accounts_list_kb(accounts: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    kb: List[List[InlineKeyboardButton]] = []
    for acc in accounts:
        kb.append([InlineKeyboardButton(text=f"🔑 {acc['name']}", callback_data=f"accshare_{acc['id']}")])
    kb.append([InlineKeyboardButton(text="🔙 В админку", callback_data="admin_menu")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_account_shares_management_kb(
    acc_id: int, shared_users: List[Dict[str, Any]], has_available_users: bool
) -> InlineKeyboardMarkup:
    kb: List[List[InlineKeyboardButton]] = []
    for u in shared_users:
        name = u.get("username") or u.get("first_name") or str(u["user_id"])
        kb.append(
            [InlineKeyboardButton(text=f"❌ Забрать доступ у {name}", callback_data=f"unshare_{acc_id}_{u['user_id']}")]
        )

    if has_available_users:
        kb.append([InlineKeyboardButton(text="➕ Выдать доступ пользователю", callback_data=f"sharepick_{acc_id}")])

    kb.append([InlineKeyboardButton(text="🔙 Назад к аккаунту", callback_data=f"view_{acc_id}")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_pick_user_to_share_kb(acc_id: int, users: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    kb: List[List[InlineKeyboardButton]] = []
    for u in users:
        name = u.get("username") or u.get("first_name") or str(u["user_id"])
        kb.append([InlineKeyboardButton(text=f"👤 {name}", callback_data=f"doshare_{acc_id}_{u['user_id']}")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"accshare_{acc_id}")])
    return InlineKeyboardMarkup(inline_keyboard=kb)
