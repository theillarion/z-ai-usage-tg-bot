"""Alert management handlers: configure, add presets, custom threshold, delete with user scoping."""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import config
from app.database import (
    add_alert,
    check_account_access,
    delete_alert,
    get_account_by_id,
    get_alerts_by_account,
)
from app.keyboards import (
    get_add_alert_menu_kb,
    get_alert_saved_kb,
    get_alerts_list_kb,
    get_custom_unit_choice_kb,
)
from app.states import CustomAlertFSM

router = Router(name="alerts")


@router.callback_query(F.data.startswith("alerts_"))
async def acc_alerts_cb(callback: CallbackQuery):
    """Render list of alerts configured by current user for the selected account."""
    acc_id = int(callback.data.split("_")[1])
    from_user = getattr(callback, "from_user", None)
    user_id = getattr(from_user, "id", config.OWNER_ID) if from_user else config.OWNER_ID

    acc = get_account_by_id(acc_id)
    if not acc:
        await callback.answer("Аккаунт не найден", show_alert=True)
        return

    has_access, _ = check_account_access(acc_id, user_id)
    if not has_access:
        await callback.answer("Доступ запрещен.", show_alert=True)
        return

    alerts = get_alerts_by_account(acc_id, user_id=user_id)
    text = f"🔔 <b>Настройки алертов для аккаунта:</b> {acc['name']}\n\n"
    if not alerts:
        text += "<i>У вас пока нет настроенных алертов для этого аккаунта.</i>\n"
    else:
        text += "<b>Активные алерты:</b>\n"
        for idx, a in enumerate(alerts, 1):
            unit_str = "5-часовой" if a["limit_unit"] == 3 else "Недельный"
            if a["alert_type"] == "threshold":
                pct = a["threshold_pct"]
                pct_val = int(pct) if isinstance(pct, (int, float)) and float(pct).is_integer() else pct
                rule_str = f"⏳ {unit_str} > {pct_val}%"
            else:
                rule_str = f"⚡️ {unit_str} Burn Rate (>50% за пол-периода)"
            text += f"{idx}. {rule_str}\n"

    kb = get_alerts_list_kb(acc_id, alerts)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("delalert_"))
async def del_alert_cb(callback: CallbackQuery):
    """Delete an alert and reload the account's alerts menu."""
    parts = callback.data.split("_")
    alert_id = int(parts[1])
    acc_id = int(parts[2])
    delete_alert(alert_id)
    await callback.answer("Алерт удален!")
    callback.data = f"alerts_{acc_id}"
    await acc_alerts_cb(callback)


@router.callback_query(F.data.startswith("addalert_"))
async def add_alert_menu_cb(callback: CallbackQuery):
    """Show preset alert choices and custom percentage option."""
    acc_id = int(callback.data.split("_")[1])
    from_user = getattr(callback, "from_user", None)
    user_id = getattr(from_user, "id", config.OWNER_ID) if from_user else config.OWNER_ID

    acc = get_account_by_id(acc_id)
    if not acc:
        await callback.answer("Аккаунт не найден", show_alert=True)
        return

    has_access, _ = check_account_access(acc_id, user_id)
    if not has_access:
        await callback.answer("Доступ запрещен.", show_alert=True)
        return


    text = f"➕ <b>Выберите тип алерта для:</b> {acc['name']}"
    kb = get_add_alert_menu_kb(acc_id)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("setalt_"))
async def set_alert_preset_cb(callback: CallbackQuery):
    """Save a preset alert (threshold or burn rate) and reload alerts list."""
    parts = callback.data.split("_")
    acc_id = int(parts[1])
    alert_type = parts[2]
    if alert_type == "burn":
        alert_type = "burn_rate"
    unit = int(parts[3])
    pct = float(parts[4])

    from_user = getattr(callback, "from_user", None)
    user_id = getattr(from_user, "id", config.OWNER_ID) if from_user else config.OWNER_ID
    add_alert(acc_id, alert_type, unit, pct, user_id=user_id)
    await callback.answer("Алерт успешно добавлен!")
    callback.data = f"alerts_{acc_id}"
    await acc_alerts_cb(callback)


@router.callback_query(F.data.startswith("customunit_"))
async def custom_unit_choice_cb(callback: CallbackQuery):
    """Prompt user to choose 5h or weekly unit for custom alert."""
    acc_id = int(callback.data.split("_")[1])
    text = "Для какого лимита настроить порог срабатывания?"
    kb = get_custom_unit_choice_kb(acc_id)
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("customchoose_"))
async def custom_choose_cb(callback: CallbackQuery, state: FSMContext):
    """Prompt user for numeric percentage and enter CustomAlertFSM.pct state."""
    parts = callback.data.split("_")
    acc_id = int(parts[1])
    unit = int(parts[2])

    await state.update_data(acc_id=acc_id, unit=unit)
    await state.set_state(CustomAlertFSM.pct)

    unit_str = "5-часового" if unit == 3 else "недельного"
    await callback.message.answer(
        f"Введите процент использования для <b>{unit_str} лимита</b> (число от 1 до 99):\n"
        f"Например: <code>70</code>\n\n"
        f"<i>Для отмены отправьте /cancel</i>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(CustomAlertFSM.pct)
async def custom_alert_pct_input(message: Message, state: FSMContext):
    """Validate user input percentage and create custom threshold alert."""
    text = message.text.strip().replace("%", "")
    try:
        pct = float(text)
        if not (1 <= pct <= 99):
            raise ValueError()
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректное число от 1 до 99 (например, 75).")
        return

    data = await state.get_data()
    acc_id = data["acc_id"]
    unit = data["unit"]

    from_user = getattr(message, "from_user", None)
    user_id = getattr(from_user, "id", config.OWNER_ID) if from_user else config.OWNER_ID
    add_alert(acc_id, "threshold", unit, pct, user_id=user_id)
    await state.clear()


    unit_str = "5-часового" if unit == 3 else "недельного"
    pct_display = int(pct) if pct.is_integer() else pct
    kb = get_alert_saved_kb(acc_id)
    await message.answer(
        f"✅ Алерт сохранен: оповестить, когда расход <b>{unit_str} лимита</b> превысит <b>{pct_display}%</b>!",
        reply_markup=kb,
        parse_mode="HTML",
    )
