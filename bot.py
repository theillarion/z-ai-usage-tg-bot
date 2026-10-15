import asyncio
import logging
import sqlite3
import os
import sys
import requests
import re
from datetime import datetime, timezone, timedelta
import pytz
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from typing import Callable, Dict, Any, Awaitable

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", 0))

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()

class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = data.get("event_from_user")
        if user and user.id != OWNER_ID:
            if isinstance(event, Message):
                await event.answer(f'Бот отвечает только закрытому кругу лиц. Для связи пишите <a href="tg://user?id={OWNER_ID}">владельцу</a>.', parse_mode="HTML")
            elif isinstance(event, CallbackQuery):
                await event.answer("Доступ запрещен.", show_alert=True)
            return
        return await handler(event, data)

dp.message.middleware(AuthMiddleware())
dp.callback_query.middleware(AuthMiddleware())

# --- DB Setup ---
DB_DIR = "/data"
# Fallback for local run without docker
if not os.path.exists(DB_DIR) and not os.environ.get("DOCKER"):
    DB_DIR = "./data"
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)

DB_PATH = os.path.join(DB_DIR, "database.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS accounts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT,
                  token TEXT)''')
    conn.commit()
    conn.close()

def add_account(name, token):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO accounts (name, token) VALUES (?, ?)", (name, token))
    conn.commit()
    conn.close()

def get_accounts():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name, token FROM accounts")
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "token": r[2]} for r in rows]

def get_account_by_id(acc_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name, token FROM accounts WHERE id = ?", (acc_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "name": row[1], "token": row[2]}
    return None

def delete_account(acc_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM accounts WHERE id = ?", (acc_id,))
    conn.commit()
    conn.close()

# --- Helpers ---
def format_ts_msk(ts):
    if not ts:
        return "Неизвестно"
    if isinstance(ts, (int, float)):
        ts_sec = ts / 1000.0 if ts > 9999999999 else float(ts)
        try:
            msk_tz = pytz.timezone("Europe/Moscow")
            dt = datetime.fromtimestamp(ts_sec, tz=pytz.utc).astimezone(msk_tz)
            return dt.strftime('%Y-%m-%d %H:%M:%S МСК')
        except Exception:
            try:
                msk_tz = timezone(timedelta(hours=3))
                dt = datetime.fromtimestamp(ts_sec, tz=timezone.utc).astimezone(msk_tz)
                return dt.strftime('%Y-%m-%d %H:%M:%S МСК')
            except Exception:
                return str(ts)
    if isinstance(ts, str):
        return ts
    return str(ts)

def check_token(token):
    url_quota = "https://api.z.ai/api/monitor/usage/quota/limit"
    url_sub_list = "https://api.z.ai/api/biz/subscription/list"
    url_sub_legacy = "https://chat.z.ai/api/v1/users/user/subscription"
    
    base_headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:154.0) Gecko/20100101 Firefox/154.0",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://z.ai",
        "Referer": "https://z.ai/",
        "Sec-Fetch-Mode": "cors"
    }
    
    headers_attempts = [
        base_headers,
        {
            **base_headers,
            "Bigmodel-Organization": "org-159Dbe6850324FBF8641C53D400Af618",
            "Bigmodel-Project": "proj_FE43189e8bf8485d85DEdeb7425FB779"
        }
    ]
    
    last_err = "Unknown error"
    response_data = None
    successful_headers = None
    
    for headers in headers_attempts:
        try:
            response = requests.get(url_quota, headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 200:
                    r_data = data.get("data", {})
                    response_data = r_data
                    successful_headers = headers
                    # Если получили непустые лимиты, останавливаемся
                    if r_data.get("limits"):
                        break
                else:
                    last_err = data.get("msg") or f"API error code {data.get('code')}"
            else:
                last_err = f"HTTP Error {response.status_code}"
        except Exception as e:
            last_err = str(e)
            
    if response_data is None:
        return False, last_err
        
    quota_data = response_data
    req_headers = successful_headers or base_headers
    
    # Пытаемся получить информацию о подписке из /biz/subscription/list (новый API для Coding Plan)
    sub_title = None
    sub_end = None
    sub_autorenew = None
    
    try:
        res_sub = requests.get(url_sub_list, headers=req_headers, timeout=5)
        if res_sub.status_code == 200:
            sub_json = res_sub.json()
            if sub_json.get("code") == 200:
                records = sub_json.get("data")
                if isinstance(records, list) and records:
                    active = next((s for s in records if s.get("inCurrentPeriod")), records[0])
                    prod = active.get("productName") or "GLM Coding Plan"
                    val = active.get("value") or ""
                    ver = active.get("version") or ""
                    parts = [p for p in [prod, val, f"({ver})" if ver else ""] if p]
                    sub_title = " - ".join(parts[:2]) + (f" {parts[2]}" if len(parts) > 2 else "")
                    
                    expire = active.get("nextRenewTime")
                    if not expire and active.get("valid"):
                        matches = re.findall(r'\d{4}[-/.]\d{2}[-/.]\d{2}(?:\s+\d{2}:\d{2}(?::\d{2})?)?', str(active.get("valid")))
                        if len(matches) > 1:
                            expire = matches[-1]
                        elif len(matches) == 1:
                            expire = matches[0]
                    if not expire:
                        expire = active.get("subscriptionEndDate") or active.get("expire_at") or active.get("end_time")
                    
                    sub_end = expire
                    sub_autorenew = active.get("autoRenew")
    except Exception as e:
        logging.debug(f"Subscription list error: {e}")
        
    # Резервная попытка получить дату окончания подписки из старого chat API
    if not sub_end:
        try:
            res_sub = requests.get(url_sub_legacy, headers=req_headers, timeout=5)
            if res_sub.status_code == 200:
                sub_data = res_sub.json()
                if sub_data.get("code") == 0 and sub_data.get("data"):
                    s_data = sub_data.get("data", {})
                    sub_end = s_data.get("expire_at") or s_data.get("end_time") or s_data.get("current_period_end")
        except Exception:
            pass
            
    quota_data["plan_title"] = sub_title
    quota_data["subscription_end"] = sub_end
    quota_data["auto_renew"] = sub_autorenew
    return True, quota_data

def format_limits_text(acc_name, data):
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
        msg += f"🔹 <b>Подписка:</b> Активна\n"
        
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
        
        # Определение периода лимита
        if l_unit == 3:
            time_title = f"{l_number}-часовой лимит" if l_number else "5-часовой лимит"
            icon = "⏳"
        elif l_unit == 6:
            time_title = f"{l_number}-недельный лимит" if (l_number and l_number != 1) else "Недельный лимит"
            icon = "📅"
        elif l_unit == 5:
            time_title = f"{l_number}-месячный лимит" if (l_number and l_number != 1) else "Месячный лимит"
            icon = "🗓"
        elif l_unit == 1:
            time_title = f"{l_number}-дневный лимит" if (l_number and l_number != 1) else "Суточный лимит"
            icon = "⏰"
        else:
            time_title = f"Лимит (unit={l_unit})"
            icon = "⏱"
            
        if l_type == "CREDIT_LIMIT":
            # Новый формат подписки GLM Coding Plan (Credits)
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
            # Предыдущий формат подписки (Tokens)
            count_str = ""
            if current_val is not None and usage is not None and (current_val != 0 or usage != 0):
                count_str = f" ({current_val} / {usage} Tokens)"
            msg += f"{icon} <b>{time_title}:</b> Использовано {percentage}%{count_str}\n"
            if next_reset:
                msg += f"   Сброс: {format_ts_msk(next_reset)}\n\n"
            else:
                msg += "\n"
                
        elif l_type == "TIME_LIMIT":
            # Лимиты на вызовы инструментов (Web Search, Web Reader, Zread)
            rem_str = f"Осталось {remaining} из {usage}" if (remaining is not None and usage is not None) else f"Использовано {percentage}%"
            msg += f"🛠 <b>Tools (MCP):</b> {rem_str}\n"
            if next_reset:
                msg += f"   Сброс: {format_ts_msk(next_reset)}\n"
            details = limit.get("usageDetails", [])
            if details:
                tool_names = {
                    "search-prime": "Web Search",
                    "search-prime-claude": "Web Search",
                    "web-reader": "Web Reader",
                    "zread": "Zread"
                }
                for d in details:
                    m_code = d.get("modelCode", "")
                    name = tool_names.get(m_code, m_code)
                    u = d.get("usage", 0)
                    msg += f"   - {name}: {u}\n"
            msg += "\n"
            
        else:
            # Универсальный вывод для любых других типов квот
            unit_name = "Credits" if "CREDIT" in l_type else ("Tokens" if "TOKEN" in l_type else "")
            count_str = f" ({current_val} / {usage} {unit_name})".strip() if (current_val is not None and usage is not None) else ""
            msg += f"{icon} <b>{time_title} ({l_type}):</b> Использовано {percentage}%{count_str}\n"
            if next_reset:
                msg += f"   Сброс: {format_ts_msk(next_reset)}\n\n"
            else:
                msg += "\n"
                
    return msg

# --- States ---
class AddAccountFSM(StatesGroup):
    token = State()
    name = State()

# --- Handlers ---
@router.message(CommandStart())
async def start_cmd(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить аккаунт", callback_data="add_acc")],
        [InlineKeyboardButton(text="📋 Мои аккаунты", callback_data="list_accs")],
        [InlineKeyboardButton(text="ℹ️ О проекте", callback_data="author_info")]
    ])
    await message.answer("Привет! Я приватный бот для мониторинга лимитов Z.ai.\nЧто будем делать?", reply_markup=kb)

@router.callback_query(F.data == "author_info")
async def author_info_cb(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="start_menu")]
    ])
    await callback.message.edit_text(
        f"🤖 <b>О проекте:</b> \nБот для мониторинга лимитов Z.ai.\n\n"
        f"👨‍💻 <b>Владелец:</b> <a href='tg://user?id={OWNER_ID}'>@theillarion</a>\n"
        f"🐙 <b>Исходный код:</b> <a href='https://github.com/theillarion/z-ai-usage-tg-bot'>GitHub Repository</a>\n\n"
        f"🏷 <b>Версия:</b> v2.1 (GLM V3 Credits Support)",
        reply_markup=kb,
        parse_mode="HTML",
        disable_web_page_preview=True
    )
    await callback.answer()

@router.callback_query(F.data == "add_acc")
async def add_acc_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Пришли мне твой API ключ (Bearer token) от Z.ai.\n\n"
        "💡 <i>Подсказка: ты можешь сгенерировать постоянный API-ключ на странице "
        "https://z.ai/manage-apikey</i>",
        parse_mode="HTML",
        disable_web_page_preview=True
    )
    await state.set_state(AddAccountFSM.token)
    await callback.answer()

@router.message(AddAccountFSM.token)
async def add_acc_token(message: Message, state: FSMContext):
    token = message.text.strip()
    if '…' in token or '\u2026' in token:
        await message.answer("❌ Ошибка: В токене есть многоточие. Скопируй ключ целиком!")
        return

    # Очистка токена
    token = token.encode('ascii', 'ignore').decode('ascii')
    
    if token.startswith("Bearer "):
        token = token[7:]
    
    msg = await message.answer("🔄 Проверяю токен...")
    ok, data_or_err = check_token(token)
    
    if ok:
        await state.update_data(token=token)
        await msg.edit_text("✅ Токен рабочий!\nКак назовем этот аккаунт? (например, 'Основной')")
        await state.set_state(AddAccountFSM.name)
    else:
        await msg.edit_text(f"❌ Ошибка проверки токена:\n{data_or_err}\n\nПопробуй прислать другой токен или /cancel для отмены.")

@router.message(AddAccountFSM.name)
async def add_acc_name(message: Message, state: FSMContext):
    name = message.text.strip()
    data = await state.get_data()
    token = data["token"]
    
    add_account(name, token)
    await state.clear()
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Главное меню", callback_data="start_menu")]
    ])
    await message.answer(f"🎉 Аккаунт '{name}' успешно добавлен!", reply_markup=kb)

@router.callback_query(F.data == "start_menu")
async def start_menu_cb(callback: CallbackQuery):
    await start_cmd(callback.message)
    await callback.answer()

@router.callback_query(F.data == "list_accs")
async def list_accs_cb(callback: CallbackQuery):
    accs = get_accounts()
    if not accs:
        await callback.message.edit_text(
            "У вас пока нет добавленных аккаунтов.", 
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Добавить", callback_data="add_acc")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="start_menu")]
            ])
        )
        return
        
    kb = []
    for acc in accs:
        kb.append([InlineKeyboardButton(text=f"📊 {acc['name']}", callback_data=f"view_{acc['id']}")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="start_menu")])
    
    await callback.message.edit_text("Ваши аккаунты:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@router.callback_query(F.data.startswith("view_"))
async def view_acc_cb(callback: CallbackQuery):
    acc_id = int(callback.data.split("_")[1])
    acc = get_account_by_id(acc_id)
    
    if not acc:
        await callback.answer("Аккаунт не найден", show_alert=True)
        return
        
    await callback.message.edit_text(f"🔄 Запрашиваю лимиты для '{acc['name']}'...")
    
    ok, data = check_token(acc["token"])
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data=f"view_{acc_id}"), InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del_{acc_id}")],
        [InlineKeyboardButton(text="🔙 К списку", callback_data="list_accs")]
    ])
    
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
            await callback.message.edit_text(f"❌ Ошибка получения лимитов для '{acc['name']}':\n{data}", reply_markup=kb)
        except Exception:
            pass

@router.callback_query(F.data.startswith("del_"))
async def del_acc_cb(callback: CallbackQuery):
    acc_id = int(callback.data.split("_")[1])
    delete_account(acc_id)
    await callback.answer("Удалено!")
    await list_accs_cb(callback)

async def main():
    init_db()
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    if not BOT_TOKEN or not OWNER_ID:
        logging.error("BOT_TOKEN and OWNER_ID must be set!")
        sys.exit(1)
    asyncio.run(main())
