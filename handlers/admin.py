# handlers/admin.py
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.db import db
from config import ADMIN_IDS
from states.admin import AdminState
from services.balance import change_balance
from services.settings import (
    get_channels,
    set_channels,
    get_requisite,
    set_requisite,
    get_duel_log_channel,
    set_duel_log_channel,
    get_support_url,
    set_support_url,
)


router = Router()


# -------------------------
#   /admin PANEL
# -------------------------
@router.message(F.text == "/admin")
async def admin_panel(msg: Message):
    if msg.from_user.id not in ADMIN_IDS:
        return

    kb = admin_menu_keyboard()

    await msg.answer(
        "<b>Админ-панель</b>\nВыберите раздел 👇",
        reply_markup=kb.as_markup()
    )


# ---------------------------------------------------
#  WITHDRAWAL REQUESTS
# ---------------------------------------------------
@router.callback_query(F.data == "admin_withdraws")
async def admin_withdraws(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        return

    rows = await db.fetchall(
        "SELECT id, user_id, amount, wallet, created_at "
        "FROM withdrawals WHERE status='pending' ORDER BY created_at ASC"
    )

    if not rows:
        return await call.message.edit_text("🌿 Все чисто. Ожидающих выводов нет.")

    kb = InlineKeyboardBuilder()
    text = "<b>Ожидающие выводы:</b>\n\n"

    for wid, uid, amount, wallet, created in rows:
        text += (
            f"🧾 <b>#{wid}</b>\n"
            f"👤 Пользователь: <code>{uid}</code>\n"
            f"💵 Сумма: <b>{amount}$</b>\n"
            f"🏦 Кошелёк: <code>{wallet}</code>\n"
            f"⏱ Создан: {created}\n\n"
        )

        kb.button(text=f"✅ #{wid}", callback_data=f"admin_ok:{wid}")
        kb.button(text=f"❌ #{wid}", callback_data=f"admin_no:{wid}")

    kb.adjust(2)

    await call.message.edit_text(text, reply_markup=kb.as_markup())


# ---------------------------------------------------
#  APPROVE WITHDRAWAL
# ---------------------------------------------------
@router.callback_query(F.data.startswith("admin_ok:"))
async def admin_withdraw_approve(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        return

    wid = call.data.split(":")[1]

    await db.execute("UPDATE withdrawals SET status='approved', processed_at=datetime('now') WHERE id=?", (wid,))
    await call.answer(f"Вывод #{wid} одобрен ✔", show_alert=True)

    return await admin_withdraws(call)


# ---------------------------------------------------
#  DECLINE WITHDRAWAL
# ---------------------------------------------------
@router.callback_query(F.data.startswith("admin_no:"))
async def admin_withdraw_decline(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        return

    wid = call.data.split(":")[1]

    row = await db.fetchone(
        "SELECT user_id, amount FROM withdrawals WHERE id=?", (wid,)
    )

    if row:
        uid, amount = row
        await change_balance(uid, amount)

    await db.execute(
        "UPDATE withdrawals SET status='declined', processed_at=datetime('now') WHERE id=?",
        (wid,)
    )

    await call.answer(f"Вывод #{wid} отклонён ❌", show_alert=True)

    return await admin_withdraws(call)


# ---------------------------------------------------
#  ADD BALANCE (START)
# ---------------------------------------------------
@router.callback_query(F.data == "admin_add_balance")
async def admin_add_balance_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS:
        return

    await state.set_state(AdminState.waiting_user_id)
    await call.message.edit_text("Введите ID пользователя, которому нужно пополнить баланс 👇")


# ---------------------------------------------------
#  INPUT USER ID
# ---------------------------------------------------
@router.message(AdminState.waiting_user_id)
async def admin_add_balance_user(msg: Message, state: FSMContext):
    try:
        uid = int(msg.text)
    except:
        return await msg.answer("Некорректный ID. Попробуйте снова.")

    await state.update_data(uid=uid)
    await state.set_state(AdminState.waiting_amount)
    await msg.answer("Введите сумму для начисления 💵")


# ---------------------------------------------------
#  INPUT AMOUNT
# ---------------------------------------------------
@router.message(AdminState.waiting_amount)
async def admin_add_balance_amount(msg: Message, state: FSMContext):
    try:
        amount = float(msg.text)
    except:
        return await msg.answer("Введена некорректная сумма.")

    data = await state.get_data()
    uid = data["uid"]

    await change_balance(uid, amount)

    await msg.answer(
        f"💰 Пользователю <code>{uid}</code> начислено <b>{amount}$</b>."
    )
    await state.clear()


# ---------------------------------------------------
#  SETTINGS HUB
# ---------------------------------------------------
def admin_menu_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="📤 Выводы", callback_data="admin_withdraws")
    kb.button(text="💳 Начислить баланс", callback_data="admin_add_balance")
    kb.button(text="⚙️ Настройки", callback_data="admin_settings")
    kb.button(text="📈 Статистика", callback_data="admin_stats")
    kb.adjust(2, 2)
    return kb


@router.callback_query(F.data == "admin_settings")
async def admin_settings(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        return
    kb = InlineKeyboardBuilder()
    kb.button(text="🔗 Каналы подписки", callback_data="admin_channels")
    kb.button(text="💼 Реквизиты", callback_data="admin_requisites")
    kb.button(text="🎯 Duel log chat", callback_data="admin_duel_log")
    kb.button(text="🛟 Саппорт", callback_data="admin_support")
    kb.button(text="⬅️ В панель", callback_data="admin_home")
    kb.adjust(1, 1, 1, 1)
    await call.message.edit_text("⚙️ Настройки администратора:", reply_markup=kb.as_markup())


@router.callback_query(F.data == "admin_home")
async def admin_home(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        return
    await call.message.edit_text(
        "<b>Админ-панель</b>\nВыберите раздел 👇",
        reply_markup=admin_menu_keyboard().as_markup(),
    )


# ---- Channels ----
@router.callback_query(F.data == "admin_channels")
async def admin_channels(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS:
        return
    channels = await get_channels()
    text = (
        "🔗 Текущие каналы подписки:\n"
        f"{', '.join(channels) if channels else '—'}\n\n"
        "Отправьте новые через запятую или пробел."
    )
    await state.set_state(AdminState.waiting_channels)
    await call.message.edit_text(text)


@router.message(AdminState.waiting_channels)
async def admin_channels_set(msg: Message, state: FSMContext):
    if msg.from_user.id not in ADMIN_IDS:
        return
    raw = msg.text.replace(",", " ")
    channels = [c for c in raw.split() if c]
    await set_channels(channels)
    await state.clear()
    await msg.answer("Каналы обновлены.", reply_markup=admin_menu_keyboard().as_markup())


# ---- Requisites ----
@router.callback_query(F.data == "admin_requisites")
async def admin_requisites(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        return
    rocket = await get_requisite("rocket_bot")
    crypto = await get_requisite("crypto_bot")
    text = (
        "💼 Реквизиты:\n"
        f"Rocket: {rocket}\n"
        f"Crypto: {crypto}\n\n"
        "Выберите, что изменить."
    )
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ Rocket", callback_data="admin_req:rocket_bot")
    kb.button(text="✏️ Crypto", callback_data="admin_req:crypto_bot")
    kb.button(text="⬅️ Назад", callback_data="admin_settings")
    kb.adjust(2, 1)
    await call.message.edit_text(text, reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("admin_req:"))
async def admin_req_edit(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS:
        return
    key = call.data.split(":")[1]
    await state.update_data(req_key=key)
    await state.set_state(AdminState.waiting_requisite_value)
    await call.message.edit_text("Отправьте новое значение ссылки/токена.")


@router.message(AdminState.waiting_requisite_value)
async def admin_req_save(msg: Message, state: FSMContext):
    if msg.from_user.id not in ADMIN_IDS:
        return
    data = await state.get_data()
    key = data.get("req_key")
    if not key:
        await state.clear()
        return await msg.answer("Ключ утерян, попробуйте снова.", reply_markup=admin_menu_keyboard().as_markup())
    await set_requisite(key, msg.text.strip())
    await state.clear()
    await msg.answer("Обновлено.", reply_markup=admin_menu_keyboard().as_markup())


# ---- Duel log chat ----
@router.callback_query(F.data == "admin_duel_log")
async def admin_duel_log(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS:
        return
    current = await get_duel_log_channel()
    text = (
        f"🎯 Текущий лог-чат дуэлей: {current or 'не задан'}\n"
        "Отправьте ID чата (-100...) или 0 чтобы выключить."
    )
    await state.set_state(AdminState.waiting_duel_log)
    await call.message.edit_text(text)


@router.message(AdminState.waiting_duel_log)
async def admin_duel_log_set(msg: Message, state: FSMContext):
    if msg.from_user.id not in ADMIN_IDS:
        return
    try:
        val = int(msg.text.strip())
    except Exception:
        return await msg.answer("Введите числовой ID или 0.")
    await set_duel_log_channel(None if val == 0 else val)
    await state.clear()
    await msg.answer("Лог-чат обновлён.", reply_markup=admin_menu_keyboard().as_markup())


# ---- Support link ----
@router.callback_query(F.data == "admin_support")
async def admin_support(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS:
        return
    current = await get_support_url()
    text = f"🛟 Текущая ссылка поддержки: {current or 'не задана'}\nОтправьте новую ссылку или 0 чтобы очистить."
    await state.set_state(AdminState.waiting_requisite_key)
    await state.update_data(req_key="support_url")
    await call.message.edit_text(text)


@router.message(AdminState.waiting_requisite_key)
async def admin_support_save(msg: Message, state: FSMContext):
    if msg.from_user.id not in ADMIN_IDS:
        return
    data = await state.get_data()
    if data.get("req_key") != "support_url":
        return
    value = msg.text.strip()
    if value == "0":
        value = ""
    await set_support_url(value or None)
    await state.clear()
    await msg.answer("Ссылка поддержки обновлена.", reply_markup=admin_menu_keyboard().as_markup())


# ---------------------------------------------------
#  ADVANCED STATS PANEL
# ---------------------------------------------------
@router.callback_query(F.data == "admin_stats")
async def admin_stats(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        return

    users = await db.fetchone("SELECT COUNT(*) FROM users")
    total_users = users[0] if users else 0

    games_count = await db.fetchone("SELECT COUNT(*) FROM games")
    total_games = games_count[0] if games_count else 0

    wager_row = await db.fetchone("SELECT COALESCE(SUM(bet),0) FROM games")
    total_wagered = wager_row[0] if wager_row else 0

    deposits_row = await db.fetchone(
        "SELECT COALESCE(SUM(amount),0) FROM transactions WHERE type='deposit'"
    )
    total_deposits = deposits_row[0] if deposits_row else 0

    withdrawals_row = await db.fetchone(
        "SELECT COALESCE(SUM(amount),0) FROM withdrawals WHERE status='approved'"
    )
    total_withdraws = withdrawals_row[0] if withdrawals_row else 0

    profit = (total_deposits or 0) - (total_withdraws or 0)

    text = (
        "<b>📈 Статистика</b>\n\n"
        f"👥 Пользователи: <b>{total_users}</b>\n"
        f"🎮 Игр сыграно: <b>{total_games}</b>\n"
        f"💵 Оборот ставок: <b>{total_wagered:.2f}$</b>\n\n"
        f"💰 Депозиты: <b>{total_deposits:.2f}$</b>\n"
        f"📤 Выводы (одобрено): <b>{total_withdraws:.2f}$</b>\n"
        f"🔥 Профит: <b>{profit:.2f}$</b>"
    )

    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ В панель", callback_data="admin_home")
    await call.message.edit_text(text, reply_markup=kb.as_markup())
