"""Text and timestamp formatters for Telegram messages."""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional
import pytz


def format_ts_msk(ts: Any) -> str:
    """Format a timestamp into Moscow time (MSK)."""
    if not ts:
        return "Неизвестно"

    if isinstance(ts, (int, float)):
        ts_sec = ts / 1000.0 if ts > 9999999999 else float(ts)
        try:
            msk_tz = pytz.timezone("Europe/Moscow")
            dt = datetime.fromtimestamp(ts_sec, tz=pytz.utc).astimezone(msk_tz)
            return dt.strftime("%Y-%m-%d %H:%M:%S МСК")
        except Exception:
            try:
                msk_tz = timezone(timedelta(hours=3))
                dt = datetime.fromtimestamp(ts_sec, tz=timezone.utc).astimezone(msk_tz)
                return dt.strftime("%Y-%m-%d %H:%M:%S МСК")
            except Exception:
                return str(ts)

    if isinstance(ts, str):
        return ts

    return str(ts)


def format_limits_text(acc_name: str, data: Dict[str, Any]) -> str:
    """Format account quota limits and subscription status into HTML message."""
    limits = data.get("limits", [])
    level = str(data.get("level", "")).upper()
    plan_title = data.get("plan_title")
    sub_end = data.get("subscription_end")
    auto_renew = data.get("auto_renew")

    msg = f"📊 <b>Аккаунт:</b> {acc_name}\n"

    if plan_title:
        sub_display = f"{plan_title}"
        if level and level != "UNKNOWN" and level not in plan_title.upper():
            sub_display += f" ({level})"
        msg += f"🔹 <b>Подписка:</b> {sub_display}\n"
    elif level and level != "UNKNOWN":
        msg += f"🔹 <b>Подписка:</b> {level}\n"
    else:
        msg += "🔹 <b>Подписка:</b> Активна\n"

    if sub_end:
        renew_suffix = " (автопродление)" if auto_renew else ""
        msg += f"⏳ <b>Истекает:</b> {format_ts_msk(sub_end)}{renew_suffix}\n"

    msg += "\n"

    if not limits:
        msg += "<i>Лимиты не найдены.</i>\n"
        return msg

    for limit in limits:
        l_type = limit.get("type", "")
        l_unit = limit.get("unit")
        l_number = limit.get("number")
        percentage = limit.get("percentage", 0)
        next_reset = limit.get("nextResetTime")
        remaining = limit.get("remaining")
        usage = limit.get("usage")
        current_val = limit.get("currentValue")

        # Period resolution
        if l_unit == 3:
            time_title = f"{l_number}-часовой лимит" if l_number else "5-часовой лимит"
            icon = "⏳"
        elif l_unit == 6:
            time_title = (
                f"{l_number}-недельный лимит"
                if (l_number and l_number != 1)
                else "Недельный лимит"
            )
            icon = "📅"
        elif l_unit == 5:
            time_title = (
                f"{l_number}-месячный лимит"
                if (l_number and l_number != 1)
                else "Месячный лимит"
            )
            icon = "🗓"
        elif l_unit == 1:
            time_title = (
                f"{l_number}-дневный лимит"
                if (l_number and l_number != 1)
                else "Суточный лимит"
            )
            icon = "⏰"
        else:
            time_title = f"Лимит (unit={l_unit})"
            icon = "⏱"

        if l_type == "CREDIT_LIMIT":
            # GLM Coding Plan (Credits)
            count_str = ""
            if current_val is not None and usage is not None:
                count_str = f" ({current_val} / {usage} Credits)"
            elif usage is not None:
                count_str = f" (лимит: {usage} Credits)"
            msg += f"{icon} <b>{time_title}:</b> Использовано {percentage}%{count_str}\n"
            if next_reset:
                msg += f"   Сброс: {format_ts_msk(next_reset)}\n\n"
            else:
                msg += "\n"

        elif l_type == "TOKENS_LIMIT":
            # Legacy Tokens
            count_str = ""
            if (
                current_val is not None
                and usage is not None
                and (current_val != 0 or usage != 0)
            ):
                count_str = f" ({current_val} / {usage} Tokens)"
            msg += f"{icon} <b>{time_title}:</b> Использовано {percentage}%{count_str}\n"
            if next_reset:
                msg += f"   Сброс: {format_ts_msk(next_reset)}\n\n"
            else:
                msg += "\n"

        elif l_type == "TIME_LIMIT":
            # Tool calls (Web Search, Web Reader, Zread)
            rem_str = (
                f"Осталось {remaining} из {usage}"
                if (remaining is not None and usage is not None)
                else f"Использовано {percentage}%"
            )
            msg += f"🛠 <b>Tools (MCP):</b> {rem_str}\n"
            if next_reset:
                msg += f"   Сброс: {format_ts_msk(next_reset)}\n"
            details = limit.get("usageDetails", [])
            if details:
                tool_names = {
                    "search-prime": "Web Search",
                    "search-prime-claude": "Web Search",
                    "web-reader": "Web Reader",
                    "zread": "Zread",
                }
                for d in details:
                    m_code = d.get("modelCode", "")
                    name = tool_names.get(m_code, m_code)
                    u = d.get("usage", 0)
                    msg += f"   - {name}: {u}\n"
            msg += "\n"

        else:
            # Universal fallback for any other quota types
            unit_name = (
                "Credits"
                if "CREDIT" in l_type
                else ("Tokens" if "TOKEN" in l_type else "")
            )
            unit_suffix = f" {unit_name}" if unit_name else ""
            count_str = (
                f" ({current_val} / {usage}{unit_suffix})"
                if (current_val is not None and usage is not None)
                else ""
            )
            msg += f"{icon} <b>{time_title} ({l_type}):</b> Использовано {percentage}%{count_str}\n"
            if next_reset:
                msg += f"   Сброс: {format_ts_msk(next_reset)}\n\n"
            else:
                msg += "\n"

    return msg
