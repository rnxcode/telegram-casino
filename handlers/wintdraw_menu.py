from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from states.withdraw import WithdrawState
from database.db import db
from keyboards.menu import back_btn

router = Router()


# -----------------------------
# STEP 1: OPEN WITHDRAWAL MENU
# -----------------------------
@router.callback_query(F.data == "withdraw_menu")
async def withdraw_menu(call: CallbackQuery, lang: str):
    text = (
        "<b>💸 Вывод средств</b>\n\nВведите сумму, которую хотите вывести:"
        if lang == "ru" else
        "<b>💸 Withdraw funds</b>\n\nEnter the amount you want to withdraw:"
    )

    await call.message.edit_text(text, reply_markup=back_btn())
    await WithdrawState.waiting_amount.set()


# -----------------------------
# STEP 2: ENTER AMOUNT
# -----------------------------
@router.message(WithdrawState.waiting_amount)
async def withdraw_amount(msg: Message, state: FSMContext, lang: str):
    try:
        amount = float(msg.text)
        if amount <= 0:
            raise ValueError
    except:
        return await msg.answer("Введите корректную сумму." if lang=="ru" else "Enter a valid amount.")

    # Проверяем баланс
    balance_row = await db.fetchone("SELECT balance FROM users WHERE user_id=?", (msg.from_user.id,))
    balance = balance_row[0] if balance_row else 0

    if amount > balance:
        return await msg.answer(
            f"Недостаточно средств. Ваш баланс: {balance:.2f}$"
            if lang == "ru" else
            f"Insufficient funds. Your balance: {balance:.2f}$"
        )

    await state.update_data(amount=amount)

    text = (
        "Введите ваш кошелёк для вывода:" if lang=="ru"
        else "Enter your withdrawal wallet:"
    )

    await msg.answer(text)
    await WithdrawState.waiting_wallet.set()


# -----------------------------
# STEP 3: ENTER WALLET
# -----------------------------
@router.message(WithdrawState.waiting_wallet)
async def withdraw_wallet(msg: Message, state: FSMContext, lang: str):
    wallet = msg.text.strip()
    data = await state.get_data()
    amount = data["amount"]

    if len(wallet) < 5:
        return await msg.answer("Некорректный кошелёк." if lang=="ru" else "Invalid wallet.")

    await state.update_data(wallet=wallet)

    # Подтверждение
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✔️ Подтвердить" if lang=="ru" else "✔️ Confirm",
                                 callback_data="withdraw_confirm"),
            InlineKeyboardButton(text="✖️ Отменить" if lang=="ru" else "✖️ Cancel",
                                 callback_data="withdraw_cancel"),
        ]
    ])

    text = (
        f"<b>💸 Подтверждение вывода</b>\n\n"
        f"Сумма: <b>{amount:.2f}$</b>\n"
        f"Кошелёк: <code>{wallet}</code>\n\n"
        f"Все верно?" if lang=="ru"
        else
        f"<b>💸 Withdrawal confirmation</b>\n\n"
        f"Amount: <b>{amount:.2f}$</b>\n"
        f"Wallet: <code>{wallet}</code>\n\n"
        f"Is everything correct?"
    )

    await msg.answer(text, reply_markup=kb)
    await WithdrawState.confirm.set()


# -----------------------------
# STEP 4: CONFIRM
# -----------------------------
@router.callback_query(F.data == "withdraw_confirm")
async def withdraw_confirm(call: CallbackQuery, state: FSMContext, lang: str):
    data = await state.get_data()
    amount = data["amount"]
    wallet = data["wallet"]
    user_id = call.from_user.id

    # Списываем баланс сразу
    await db.execute(
        "UPDATE users SET balance = balance - ? WHERE user_id=?",
        (amount, user_id)
    )

    # Создаем заявку
    await db.execute("""
        INSERT INTO withdrawals (user_id, amount, wallet, status, created_at)
        VALUES (?, ?, ?, 'pending', datetime('now'))
    """, (user_id, amount, wallet))

    text = (
        "✅ Заявка на вывод создана.\nОжидайте подтверждения."
        if lang == "ru"
        else "✅ Withdrawal request submitted.\nAwaiting approval."
    )

    await call.message.edit_text(text)
    await state.clear()


# -----------------------------
# STEP 5: CANCEL
# -----------------------------
@router.callback_query(F.data == "withdraw_cancel")
async def withdraw_cancel(call: CallbackQuery, state: FSMContext, lang: str):
    await state.clear()

    text = (
        "❌ Вывод отменён." if lang == "ru" else "❌ Withdrawal cancelled."
    )

    await call.message.edit_text(text)
