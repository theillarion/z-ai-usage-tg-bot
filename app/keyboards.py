"""Inline keyboard builders for bot navigation and menus."""

from typing import Any, Dict, List
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить аккаунт", callback_data="add_acc")],
            [InlineKeyboardButton(text="📋 Мои аккаунты", callback_data="list_accs")],
            [InlineKeyboardButton(text="ℹ️ О проекте", callback_data="author_info")],
        ]
    )


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
        kb.append([InlineKeyboardButton(text=f"📊 {acc['name']}", callback_data=f"view_{acc['id']}")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="start_menu")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_account_view_kb(acc_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Обновить", callback_data=f"view_{acc_id}"),
                InlineKeyboardButton(text="🔔 Алерты", callback_data=f"alerts_{acc_id}"),
                InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del_{acc_id}"),
            ],
            [InlineKeyboardButton(text="🔙 К списку", callback_data="list_accs")],
        ]
    )


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
            [InlineKeyboardButton(text="⚡️ Неделя Burn Rate (>50% за 3.5д)", callback_data=f"setalt_{acc_id}_burn_6_50")],
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
