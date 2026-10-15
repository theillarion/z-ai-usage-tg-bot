"""Alert checking logic and background worker."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from aiogram import Bot

from app.database import (
    get_accounts,
    get_all_alerts,
    update_alert_triggered,
)
from app.formatters import format_ts_msk
from app.zai_client import check_token


def evaluate_alert(
    alert: Dict[str, Any],
    limits: List[Dict[str, Any]],
    now_ms: int,
) -> Tuple[bool, str, int, Optional[int], Optional[int]]:
    """
    Evaluate if an alert should trigger.
    Returns (should_trigger, trigger_reason, next_reset, current_val, usage_val).
    """
    unit = alert["limit_unit"]
    matching_limit = next((l for l in limits if l.get("unit") == unit), None)
    if not matching_limit:
        return False, "", 0, None, None

    pct = matching_limit.get("percentage", 0)
    next_reset = matching_limit.get("nextResetTime", 0) or 0
    current_val = matching_limit.get("currentValue")
    usage_val = matching_limit.get("usage")
    last_reset = alert.get("last_triggered_reset_time", 0) or 0

    # Anti-spam: check if already notified in this reset period
    if last_reset and next_reset and last_reset == next_reset:
        return False, "", next_reset, current_val, usage_val

    should_trigger = False
    trigger_reason = ""

    if alert["alert_type"] == "threshold":
        thresh = alert["threshold_pct"]
        if pct >= thresh:
            should_trigger = True
            thresh_str = int(thresh) if isinstance(thresh, (int, float)) and float(thresh).is_integer() else thresh
            trigger_reason = f"Порог <b>{thresh_str}%</b> превышен (текущий расход: <b>{pct}%</b>)"

    elif alert["alert_type"] == "burn_rate":
        window_duration_ms = (5 * 3600 * 1000) if unit == 3 else (7 * 86400 * 1000)
        remaining_ms = next_reset - now_ms if next_reset else 0

        # Consumed >= 50% while more than 50% of the period time is still remaining
        if remaining_ms > (window_duration_ms / 2) and pct >= 50:
            should_trigger = True
            trigger_reason = (
                f"⚡️ <b>Быстрый расход (Burn Rate):</b> израсходовано <b>{pct}%</b> "
                f"лимита, хотя прошло меньше половины срока!"
            )

    return should_trigger, trigger_reason, next_reset, current_val, usage_val


async def check_alerts_job(
    bot: Bot,
    owner_id: int,
    db_path: Optional[str] = None,
) -> int:
    """
    Run a single round of checks for all active alerts.
    Returns the number of triggered alerts.
    """
    alerts = get_all_alerts(db_path)
    if not alerts:
        return 0

    accounts = {acc["id"]: acc for acc in get_accounts(db_path)}
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    acc_alerts_map: Dict[int, List[Dict[str, Any]]] = {}
    for a in alerts:
        acc_alerts_map.setdefault(a["account_id"], []).append(a)

    triggered_count = 0

    for acc_id, acc_alerts in acc_alerts_map.items():
        acc = accounts.get(acc_id)
        if not acc:
            continue

        try:
            ok, data = check_token(acc["token"])
        except Exception as e:
            logging.error(f"Error checking token for account {acc_id}: {e}")
            continue

        if not ok or not data:
            continue

        limits = data.get("limits", [])
        if not limits:
            continue

        for a in acc_alerts:
            (
                should_trigger,
                trigger_reason,
                next_reset,
                current_val,
                usage_val,
            ) = evaluate_alert(a, limits, now_ms)

            if should_trigger:
                unit = a["limit_unit"]
                unit_name = (
                    "5-часовой"
                    if unit == 3
                    else ("Недельный" if unit == 6 else f"Лимит unit={unit}")
                )
                count_str = (
                    f" ({current_val} / {usage_val} Credits)"
                    if (current_val is not None and usage_val is not None)
                    else ""
                )
                alert_text = (
                    f"🔔 <b>Алерт по аккаунту:</b> {acc['name']}\n\n"
                    f"📊 <b>Квота:</b> {unit_name}\n"
                    f"⚠️ <b>Причина:</b> {trigger_reason}{count_str}\n"
                    f"⏳ <b>Сброс лимита:</b> {format_ts_msk(next_reset)}\n"
                )
                target_user = a.get("user_id") or owner_id
                try:
                    await bot.send_message(target_user, alert_text, parse_mode="HTML")
                    update_alert_triggered(a["id"], next_reset or 1, db_path)
                    triggered_count += 1
                except Exception as e:
                    logging.error(f"Failed to send alert to {target_user}: {e}")

    return triggered_count



async def alerts_background_worker(
    bot: Bot,
    owner_id: int,
    check_interval: int = 300,
    initial_delay: int = 10,
    db_path: Optional[str] = None,
    stop_event: Optional[asyncio.Event] = None,
) -> None:
    """Continuous background worker that periodically triggers check_alerts_job."""
    if initial_delay > 0:
        if stop_event:
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=initial_delay)
                return
            except asyncio.TimeoutError:
                pass
        else:
            await asyncio.sleep(initial_delay)

    while True:
        if stop_event and stop_event.is_set():
            break
        try:
            await check_alerts_job(bot, owner_id, db_path)
        except Exception as e:
            logging.error(f"Error in alerts background worker: {e}")

        if stop_event:
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=check_interval)
                break
            except asyncio.TimeoutError:
                pass
        else:
            await asyncio.sleep(check_interval)
