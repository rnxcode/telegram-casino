from aiogram import Router, F, Bot
from aiogram.types import (
    CallbackQuery, Message, InlineKeyboardMarkup,
    InlineKeyboardButton, PreCheckoutQuery, LabeledPrice
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from decimal import Decimal

from states.deposit import DepositState
from keyboards.menu import main_menu
from keyboards.deposit import deposit_keyboard, crypto_check_keyboard
from services.payments.crypto import create_crypto_invoice, check_crypto_payment as crypto_check_payment
from services.payments.rocket import check_rocket_receipt, process_rocket_payment
from services.balance import change_balance
from database.db import db
from config import settings

router = Router()

# ----------------------------
# STATES
# ----------------------------

class StarsPaymentStates(StatesGroup):
    waiting_stars_amount = State()


# ----------------------------
# BACK
# ----------------------------

@router.callback_query(F.data == "dep_back")
async def dep_back(call: CallbackQuery, lang: str, state: FSMContext):
    await state.clear()

    await call.message.edit_text(
        "Выберите действие:" if lang == "ru" else "Choose an option:",
        reply_markup=main_menu(lang)
    )


# ----------------------------
# OPEN MENU
# ----------------------------

@router.callback_query(F.data == "deposit")
async def open_deposit(call: CallbackQuery, lang: str):
    await call.message.edit_text(
        "💰 Выберите способ пополнения:"
        if lang == "ru" else "💰 Choose deposit method:",
        reply_markup=deposit_keyboard(lang)
    )


# ----------------------------
# SELECT METHOD
# ----------------------------

@router.callback_query(F.data.startswith("dep_"))
async def dep_select(call: CallbackQuery, state: FSMContext, lang: str):
    method = call.data.split("_")[1]

    # Anti-spam: очистка старых стейтов
    await state.clear()

    # Rocket
    if method == "rocket":
        await state.set_state(DepositState.waiting_rocket_check)
        return await call.message.edit_text(
            "📄 Отправьте Rocket чек:" if lang == "ru" else "📄 Send Rocket receipt:"
        )

    # Stars
    if method == "stars":
        await state.set_state(StarsPaymentStates.waiting_stars_amount)
        return await call.message.edit_text(
            "Введите количество ⭐ Stars:" if lang == "ru"
            else "Enter Stars amount:"
        )

    # Crypto
    if method == "crypto":
        await state.update_data(method="crypto", lang=lang)
        await state.set_state(DepositState.waiting_amount)
        return await call.message.edit_text(
            "Введите сумму в USD:" if lang == "ru" else "Enter amount in USD:"
        )


# ----------------------------
# CRYPTO INPUT
# ----------------------------

@router.message(DepositState.waiting_amount)
async def dep_amount(msg: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")

    # Валидация суммы
    try:
        amount = float(msg.text)
        if not 1 <= amount <= 10_000:
            raise ValueError
    except:
        return await msg.answer("Введите сумму от 1 до 10000$")

    url, invoice_id = await create_crypto_invoice(msg.from_user.id, amount)

    await msg.answer(
        ("💳 Оплатите по ссылке:\n" if lang == "ru" else "💳 Pay here:\n") + url,
        reply_markup=crypto_check_keyboard(invoice_id, lang)
    )

    await state.clear()


# ----------------------------
# ROCKET
# ----------------------------

@router.message(DepositState.waiting_rocket_check)
async def dep_rocket_check(msg: Message, state: FSMContext, lang: str):
    receipt = msg.text.strip()

    data = await check_rocket_receipt(receipt)

    if not data or not data.get("valid"):
        return await msg.answer("❌ Неверный чек" if lang=="ru" else "❌ Invalid")

    try:
        amount = float(data.get("amount", 0))
    except Exception:
        amount = 0.0

    if amount <= 0:
        return await msg.answer("❌ Неверная сумма" if lang=="ru" else "❌ Invalid amount")

    # Регистрируем платёж в pending (уникальный receipt)
    await db.upsert_pending_payment(
        user_id=msg.from_user.id,
        method="rocket",
        amount=Decimal(str(amount)),
        external_id=receipt,
        status="paid",
    )

    # Idempotent начисление
    changed = await db.mark_pending_paid(method="rocket", external_id=receipt)
    if changed:
        await change_balance(
            msg.from_user.id,
            amount,
            tx_type="deposit",
            method="rocket",
            meta={"receipt": receipt},
        )

    await msg.answer(f"✅ Зачислено {amount}$")
    await state.clear()


# ----------------------------
# CRYPTO CHECK
# ----------------------------

@router.callback_query(F.data.startswith("check_crypto:"))
async def check_crypto_payment(call: CallbackQuery, lang: str):
    invoice_id = call.data.split(":")[1]

    # Проверяем, что invoice существует
    row = await db.fetchone(
        "SELECT amount, status FROM pending_payments WHERE external_id=?",
        (invoice_id,)
    )
    if not row:
        return await call.answer("❌ Платёж не найден", show_alert=True)

    amount, status_db = row

    # Если уже обработан
    if status_db == "paid":
        return await call.answer("✔ Уже зачислено", show_alert=True)

    info = await crypto_check_payment(invoice_id)
    status = info.get("status")

    if status == "paid":
        # атомарность: отмечаем как paid, потом начисляем
        changed = await db.mark_pending_paid(method="crypto", external_id=invoice_id)
        if changed:
            await change_balance(call.from_user.id, float(amount), tx_type="deposit", method="crypto")

        return await call.message.edit_text("💰 Средства зачислены!")

    if status == "active":
        return await call.answer("⌛ Платёж в процессе", show_alert=True)

    if status == "expired":
        await db.execute("UPDATE pending_payments SET status='expired' WHERE method='crypto' AND external_id=?", (invoice_id,))
        return await call.message.edit_text("❌ Счёт истёк.")

    return await call.answer("⚠ Неизвестный статус")


# ----------------------------
# STARS INPUT
# ----------------------------

@router.message(StarsPaymentStates.waiting_stars_amount)
async def stars_amount_handler(msg: Message, state: FSMContext, bot: Bot):
    text = msg.text.strip()
    if not text.isdigit():
        return await msg.answer("Введите число")

    stars = int(text)
    if not 1 <= stars <= 10_000:
        return await msg.answer("Допустимый диапазон: 1–10000 ⭐")

    payload = f"stars_{msg.from_user.id}_{stars}"

    await db.upsert_pending_payment(
        user_id=msg.from_user.id,
        method="stars",
        amount=Decimal(str(stars)),
        external_id=payload,
        status="pending",
    )

    await bot.send_invoice(
        chat_id=msg.chat.id,
        title="Пополнение Stars",
        description="Оплата Stars",
        payload=payload,
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="Stars", amount=stars)]
    )

    await state.clear()


# ----------------------------
# STARS — PRECHECKOUT
# ----------------------------

@router.pre_checkout_query()
async def stars_pre_checkout(pcq: PreCheckoutQuery, bot: Bot):
    await bot.answer_pre_checkout_query(pcq.id, ok=True)


# ----------------------------
# STARS — SUCCESS
# ----------------------------

@router.message(F.successful_payment)
async def stars_success(msg: Message):
    payment = msg.successful_payment

    if payment.currency != "XTR":
        return

    payload = payment.invoice_payload
    amount = payment.total_amount

    # Проверяем pending
    row = await db.fetchone(
        "SELECT status FROM pending_payments WHERE external_id=? AND method='stars'",
        (payload,)
    )

    if not row:
        return await msg.answer("❌ Оплата не найдена.")

    if row[0] == "paid":
        return await msg.answer("✔ Уже зачислено")

    changed = await db.mark_pending_paid(method="stars", external_id=payload)
    if not changed:
        return await msg.answer("✔ Уже зачислено")

    usd_amount = Decimal(str(amount)) * settings.STARS_USD_RATE

    await change_balance(msg.from_user.id, float(usd_amount), tx_type="deposit", method="stars", meta={"stars": amount})

    await msg.answer(f"⭐ Успешно! Зачислено {float(usd_amount):.2f}$")
