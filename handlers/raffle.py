import random
from decimal import Decimal

from aiogram import F, Router
from aiogram.types import CallbackQuery

from database.db import db
from keyboards.raffle import (
    raffle_amounts_keyboard,
    raffle_control_keyboard,
    raffle_join_keyboard,
    raffle_menu_keyboard,
)
from services.balance import change_balance, get_balance


router = Router()


@router.callback_query(F.data == "raffle")
async def raffle_menu(call: CallbackQuery, lang: str):
    text = (
        "🎁 <b>Розыгрыши</b>\n\n"
        "Выберите взнос, мы разошлём приглашение всем игрокам. "
        "Каждый, кто нажмёт «Участвовать», вносит ту же сумму, "
        "а победитель забирает весь банк."
    )
    if lang != "ru":
        text = (
            "🎁 <b>Raffles</b>\n\n"
            "Pick an entry fee and we will broadcast the raffle to all users. "
            "Everyone who joins pays the same amount, winner takes the pot."
        )
    await call.message.edit_text(text, reply_markup=raffle_menu_keyboard(lang))


@router.callback_query(F.data == "raffle_create")
async def raffle_create(call: CallbackQuery, lang: str):
    text = (
        "Сколько ставим в банк?" if lang == "ru" else "Pick the entry amount:"
    )
    await call.message.edit_text(text, reply_markup=raffle_amounts_keyboard(lang))


@router.callback_query(F.data == "raffle_back")
async def raffle_back(call: CallbackQuery, lang: str):
    await raffle_menu(call, lang)


@router.callback_query(F.data.startswith("raffle_amount:"))
async def raffle_amount(call: CallbackQuery, lang: str):
    user_id = call.from_user.id
    amount_raw = call.data.split(":")[1]
    entry = Decimal(amount_raw)

    balance = await get_balance(user_id)
    if balance < float(entry):
        return await call.answer(
            "Недостаточно средств" if lang == "ru" else "Not enough balance",
            show_alert=True,
        )

    try:
        await change_balance(
            user_id,
            -float(entry),
            tx_type="raffle_entry",
            meta={"raffle_id": "pending"},
        )
        raffle_id = await db.create_raffle(user_id, entry)
    except Exception as exc:
        await change_balance(
            user_id,
            float(entry),
            tx_type="raffle_refund",
            meta={"reason": "create_failed"},
        )
        return await call.answer(str(exc), show_alert=True)

    text = (
        f"🔔 Розыгрыш создан.\n"
        f"Взнос: {float(entry):.2f}$ • Банк: {float(entry):.2f}$\n"
        "Мы отправили приглашение всем игрокам. "
        "Когда будете готовы — жмите «Запустить розыгрыш»."
    )
    if lang != "ru":
        text = (
            f"🔔 Raffle created.\n"
            f"Entry: {float(entry):.2f}$ • Pot: {float(entry):.2f}$\n"
            "Invite sent to all players. "
            "Press “Draw winner” when ready."
        )
    await call.message.edit_text(
        text,
        reply_markup=raffle_control_keyboard(raffle_id, lang),
    )

    await broadcast_raffle(call, raffle_id, entry, lang)


async def broadcast_raffle(call: CallbackQuery, raffle_id: int, entry: Decimal, lang: str):
    bot = call.bot
    author = call.from_user
    if author.username:
        caption = f"🎁 Новый розыгрыш!\nАвтор: @{author.username}\n"
        caption_en = f"🎁 New raffle!\nHost: @{author.username}\n"
    else:
        caption = f"🎁 Новый розыгрыш!\nАвтор: {author.full_name}\n"
        caption_en = f"🎁 New raffle!\nHost: {author.full_name}\n"
    caption += f"Взнос: {float(entry):.2f}$\nНажми, чтобы участвовать."
    caption_en += f"Entry: {float(entry):.2f}$\nTap to join."
    kb_ru = raffle_join_keyboard(raffle_id, "ru")
    kb_en = raffle_join_keyboard(raffle_id, "en")

    users = await db.fetchall("SELECT user_id, lang FROM users")
    for row in users:
        uid = int(row[0])
        lang_pref = row[1] if len(row) > 1 else "ru"
        text = caption if lang_pref == "ru" else caption_en
        try:
            await bot.send_message(
                uid,
                text,
                reply_markup=kb_ru if lang_pref == "ru" else kb_en,
                disable_web_page_preview=True,
            )
        except Exception:
            continue

    try:
        await call.answer(
            "Приглашения отправлены." if lang == "ru" else "Invites sent.",
            show_alert=False,
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("raffle_join:"))
async def raffle_join(call: CallbackQuery, lang: str):
    raffle_id = int(call.data.split(":")[1])
    raffle = await db.get_raffle(raffle_id)
    if not raffle:
        return await call.answer(
            "Розыгрыш не найден" if lang == "ru" else "Raffle not found",
            show_alert=True,
        )
    if raffle["status"] != "open":
        return await call.answer(
            "Розыгрыш завершён" if lang == "ru" else "Raffle already closed",
            show_alert=True,
        )

    entry = float(raffle["entry_amount"])
    if await get_balance(call.from_user.id) < entry:
        return await call.answer(
            "Недостаточно средств" if lang == "ru" else "Not enough balance",
            show_alert=True,
        )

    await change_balance(
        call.from_user.id,
        -entry,
        tx_type="raffle_entry",
        meta={"raffle_id": raffle_id},
    )

    status, pot = await db.add_raffle_participant(raffle_id, call.from_user.id)
    if status in ("closed", "missing"):
        await change_balance(
            call.from_user.id,
            entry,
            tx_type="raffle_refund",
            meta={"raffle_id": raffle_id},
        )
        return await call.answer(
            "Розыгрыш закрыт." if lang == "ru" else "Raffle is closed.",
            show_alert=True,
        )
    if status == "already":
        await change_balance(
            call.from_user.id,
            entry,
            tx_type="raffle_refund",
            meta={"raffle_id": raffle_id, "reason": "duplicate"},
        )
        return await call.answer(
            "Вы уже участвуете." if lang == "ru" else "You already joined.",
            show_alert=True,
        )

    await call.answer(
        f"Вы в игре! Текущий банк: {float(pot):.2f}$"
        if lang == "ru"
        else f"You're in! Current pot: {float(pot):.2f}$",
        show_alert=True,
    )


@router.callback_query(F.data.startswith("raffle_finish:"))
async def raffle_finish(call: CallbackQuery, lang: str):
    raffle_id = int(call.data.split(":")[1])
    raffle = await db.get_raffle(raffle_id)
    if not raffle:
        return await call.answer(
            "Розыгрыш не найден" if lang == "ru" else "Raffle not found",
            show_alert=True,
        )
    if raffle["creator_id"] != call.from_user.id:
        return await call.answer(
            "Только автор может завершить." if lang == "ru" else "Only host can close.",
            show_alert=True,
        )
    if raffle["status"] != "open":
        return await call.answer(
            "Уже завершено" if lang == "ru" else "Already finished",
            show_alert=True,
        )

    participants = await db.raffle_participants(raffle_id)
    if not participants:
        participants = [call.from_user.id]

    winner_id = random.choice(participants)
    await db.finish_raffle(raffle_id, winner_id)
    await change_balance(
        winner_id,
        float(raffle["pot"]),
        tx_type="raffle_win",
        meta={"raffle_id": raffle_id},
    )

    result_text = (
        f"🎲 Победитель: <a href='tg://user?id={winner_id}'>игрок</a>\n"
        f"Банк: {float(raffle['pot']):.2f}$"
    )
    if lang != "ru":
        result_text = (
            f"🎲 Winner: <a href='tg://user?id={winner_id}'>player</a>\n"
            f"Pot: {float(raffle['pot']):.2f}$"
        )

    await call.message.edit_text(result_text, disable_web_page_preview=True)

    # Уведомляем победителя
    winner_lang = await db.get_user_lang(winner_id)
    win_text = (
        f"🎉 Вы выиграли розыгрыш #{raffle_id} и получили {float(raffle['pot']):.2f}$!"
        if winner_lang == "ru"
        else f"🎉 You won raffle #{raffle_id} and received {float(raffle['pot']):.2f}$!"
    )
    try:
        await call.bot.send_message(winner_id, win_text)
    except Exception:
        pass
