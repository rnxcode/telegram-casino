from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from states.withdraw import WithdrawState
import re
from decimal import Decimal
from datetime import datetime

from services.balance import get_balance
from database.db import db

router = Router()


# ================================
#  ОТКРЫТИЕ МЕНЮ ВЫВОДА
# ================================
@router.callback_query(F.data == "withdraw_menu")
async def withdraw_menu(call: CallbackQuery, lang: str, state: FSMContext):
    await state.set_state(WithdrawState.waiting_amount)

    text = (
        "💸 <b>Вывод средств</b>\n\n"
        "Введите сумму, которую хотите вывести (в USD):"
        if lang == "ru"
        else
        "💸 <b>Withdrawal</b>\n\n"
        "Enter the amount you want to withdraw (in USD):"
    )

    await call.message.edit_text(text)


# ================================
#  СУММА ВЫВОДА
# ================================
@router.message(WithdrawState.waiting_amount)
async def withdraw_amount(msg: Message, state: FSMContext, lang: str):
    try:
        amount = Decimal(msg.text.strip())
        if amount < Decimal("5"):
            raise ValueError
    except:
        return await msg.answer(
            "Минимальная сумма вывода — <b>5$</b>."
            if lang == "ru" else
            "Minimum withdrawal is <b>$5</b>."
        )

    balance = Decimal(str(await get_balance(msg.from_user.id)))
    if amount > balance:
        return await msg.answer(
            "❌ Недостаточно средств для вывода."
            if lang == "ru" else
            "❌ Insufficient balance."
        )

    await state.update_data(amount=str(amount))
    await state.set_state(WithdrawState.waiting_wallet)

    text = (
        "Введите ваш кошелёк для вывода:\n\n"
        "• <b>USDT TRC-20</b>\n"
        "• <b>TON Wallet</b> (адрес EQ... или ton://)"
        if lang == "ru" else
        "Enter your withdrawal wallet:\n\n"
        "• <b>USDT TRC-20</b>\n"
        "• <b>TON Wallet</b> (address EQ... or ton://)"
    )

    await msg.answer(text)


# ================================
#  ПРОВЕРКА КОШЕЛЬКА + СОЗДАНИЕ ЗАЯВКИ
# ================================
@router.message(WithdrawState.waiting_wallet)
async def withdraw_wallet(msg: Message, state: FSMContext, lang: str):
    wallet = msg.text.strip()

    # --------------------------
    #  === ВАЛИДАЦИЯ TON/USDT ===
    # --------------------------
    # USDT TRC-20: Base58, starts with T, length 34
    trc20_ok = bool(re.fullmatch(r"T[1-9A-HJ-NP-Za-km-z]{33}", wallet))
    # TON: friendly address (EQ/UQ) commonly 48 chars, or ton:// scheme
    ton_ok = wallet.startswith("ton://") or bool(re.fullmatch(r"(EQ|UQ)[A-Za-z0-9_-]{46}", wallet))
    valid = trc20_ok or ton_ok

    if not valid:
        return await msg.answer(
            "❌ Неверный адрес кошелька.\nПоддерживаемые сети:\n• USDT TRC-20\n• TON"
            if lang == "ru" else
            "❌ Invalid wallet address.\nSupported networks:\n• USDT TRC-20\n• TON"
        )

    data = await state.get_data()
    amount = Decimal(str(data["amount"]))

    # --------------------------
    #  СОЗДАЁМ ЗАЯВКУ В БАЗЕ
    # --------------------------
    # Atomic: create request + deduct balance + ledger entry in one DB transaction
    now = datetime.utcnow().isoformat()
    async with db.transaction() as conn:
        cur = await conn.execute("SELECT balance FROM users WHERE user_id=?", (msg.from_user.id,))
        row = await cur.fetchone()
        before = Decimal(str(row[0])) if row else Decimal("0")
        after = before - amount
        if after < 0:
            raise ValueError("Insufficient balance")

        await conn.execute("UPDATE users SET balance=?, updated_at=? WHERE user_id=?", (float(after), now, msg.from_user.id))
        await conn.execute(
            """INSERT INTO transactions (user_id, amount, type, method, before, after, meta, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (msg.from_user.id, float(-amount), "withdraw_hold", "system", float(before), float(after), wallet, now),
        )
        await conn.execute(
            "INSERT INTO withdrawals (user_id, amount, wallet, status, created_at) VALUES (?, ?, ?, 'pending', ?)",
            (msg.from_user.id, float(amount), wallet, now),
        )

    # --------------------------
    #  ОТВЕТ ПОЛЬЗОВАТЕЛЮ
    # --------------------------
    text = (
        f"📤 <b>Заявка на вывод создана</b>\n\n"
        f"Сумма: <b>{float(amount):.2f}$</b>\n"
        f"Кошелёк:\n<code>{wallet}</code>\n\n"
        "Ожидайте обработки администрацией."
        if lang == "ru" else
        f"📤 <b>Withdrawal request submitted</b>\n\n"
        f"Amount: <b>{amount}$</b>\n"
        f"Wallet:\n<code>{wallet}</code>\n\n"
        "Please wait for manual approval."
    )

    await msg.answer(text)
    await state.clear()
