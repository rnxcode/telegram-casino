import asyncio
import random
from decimal import Decimal

from aiogram import F, Router
from aiogram.types import CallbackQuery

from database.db import db
from keyboards.duels import (
    duel_bets_keyboard,
    duel_game_keyboard,
    duel_wait_keyboard,
)
from services.balance import change_balance, get_balance
from services.referrals import award_loss_commission
from services.settings import get_duel_log_channel


router = Router()


@router.callback_query(F.data == "duels")
async def duels_menu(call: CallbackQuery, lang: str):
    text = (
        "⚔️ <b>Дуэли</b>\n\n"
        "1) выбери ставку\n"
        "2) выбери игру (кубик, дартс, футбол, баскетбол, боулинг)\n"
        "3) отправь ссылку другу или зайдёт любой по кнопке.\n\n"
        "Победитель забирает весь банк."
    )
    if lang != "ru":
        text = (
            "⚔️ <b>Duels</b>\n\n"
            "1) pick a stake\n"
            "2) choose dice, darts, football, basketball, or bowling\n"
            "3) share the duel link with a friend.\n\n"
            "Winner takes the whole pot."
        )
    await call.message.edit_text(text, reply_markup=duel_bets_keyboard(lang))


@router.callback_query(F.data.startswith("duel_bet:"))
async def handle_duel_bet(call: CallbackQuery, lang: str):
    user_id = call.from_user.id
    bet_raw = call.data.split(":")[1]
    bet = Decimal(bet_raw)

    balance = await get_balance(user_id)
    if balance < float(bet):
        return await call.answer(
            "Недостаточно средств" if lang == "ru" else "Not enough balance",
            show_alert=True,
        )

    await call.message.edit_text(
        "Выбери игру для дуэли:" if lang == "ru" else "Choose the duel game:",
        reply_markup=duel_game_keyboard(float(bet), lang),
    )


@router.callback_query(F.data.startswith("duel_game:"))
async def duel_game_selected(call: CallbackQuery, lang: str):
    _, bet_raw, game = call.data.split(":")
    bet = Decimal(bet_raw)

    user_id = call.from_user.id
    if await get_balance(user_id) < float(bet):
        return await call.answer(
            "Недостаточно средств" if lang == "ru" else "Not enough balance",
            show_alert=True,
        )

    try:
        await change_balance(
            user_id,
            -float(bet),
            tx_type="duel_bet",
            meta={"duel_id": "pending", "role": "creator", "game": game},
        )
        duel_id = await db.create_duel(user_id, bet, game)
    except Exception as exc:
        await change_balance(
            user_id,
            float(bet),
            tx_type="duel_refund",
            meta={"duel_id": "pending"},
        )
        return await call.answer(str(exc), show_alert=True)

    await send_duel_log(
        call.bot,
        f"🎯 Duel #{duel_id} created | Game: {game} | Bet: {float(bet):.2f}$ | Pot: {float(bet):.2f}$ | Host: {call.from_user.id}",
    )

    text = (
        f"🧠 Дуэль создана!\n"
        f"Игра: {game_title(game, 'ru')}\n"
        f"Ставка: {float(bet):.2f}$ • Банк: {float(bet):.2f}$\n\n"
        f"Ссылка для друга: /start duel_{duel_id}"
    )
    if lang != "ru":
        text = (
        f"🧠 Duel created!\n"
            f"Game: {game_title(game, 'en')}\n"
            f"Stake: {float(bet):.2f}$ • Pot: {float(bet):.2f}$\n\n"
            f"Share this: /start duel_{duel_id}"
        )
    await call.message.edit_text(text, reply_markup=duel_wait_keyboard(duel_id, lang))
    text = (
        f"🧠 Дуэль на {float(bet):.2f}$ создана.\n"
        "Ждём соперника..."
    )
    if lang != "ru":
        text = (
            f"🧠 Duel for {float(bet):.2f}$ created.\n"
            "Waiting for opponent..."
        )
    await call.message.edit_text(text, reply_markup=duel_wait_keyboard(duel_id, lang))


@router.callback_query(F.data.startswith("duel_cancel:"))
async def cancel_duel(call: CallbackQuery, lang: str):
    duel_id = int(call.data.split(":")[1])
    refund = await db.cancel_duel(duel_id, call.from_user.id)
    if refund <= 0:
        return await call.answer(
            "Эту дуэль нельзя отменить." if lang == "ru" else "Cannot cancel this duel.",
            show_alert=True,
        )

    await change_balance(
        call.from_user.id,
        refund,
        tx_type="duel_refund",
        meta={"duel_id": duel_id},
    )

    text = "Дуэль отменена, ставка возвращена." if lang == "ru" else "Duel cancelled, bet refunded."
    await call.message.edit_text(text, reply_markup=duel_bets_keyboard(lang))


@router.callback_query(F.data.startswith("duel_join:"))
async def join_duel(call: CallbackQuery, lang: str):
    duel_id = int(call.data.split(":")[1])
    row = await db.get_duel(duel_id)
    if not row:
        return await call.answer(
            "Дуэль не найдена." if lang == "ru" else "Duel not found.",
            show_alert=True,
        )
    if row["creator_id"] == call.from_user.id:
        return await call.answer(
            "Это ваша дуэль. Ждите соперника." if lang == "ru" else "This is your duel, waiting for opponent.",
            show_alert=True,
        )
    if row["status"] != "waiting":
        return await call.answer(
            "Дуэль уже идёт или завершена." if lang == "ru" else "Duel already taken or finished.",
            show_alert=True,
        )

    bet = float(row["bet"])
    if await get_balance(call.from_user.id) < bet:
        return await call.answer(
            "Недостаточно средств" if lang == "ru" else "Not enough balance",
            show_alert=True,
        )

    # Списываем ставку и пытаемся присоединиться
    await change_balance(
        call.from_user.id,
        -bet,
        tx_type="duel_bet",
        meta={"duel_id": duel_id, "role": "opponent"},
    )

    status, pot = await db.join_duel(duel_id, call.from_user.id)
    if status != "joined":
        await change_balance(
            call.from_user.id,
            bet,
            tx_type="duel_refund",
            meta={"duel_id": duel_id},
        )
        msg = "Дуэль уже занята." if lang == "ru" else "Duel already taken."
        return await call.answer(msg, show_alert=True)

    await run_duel(call, duel_id, row["creator_id"], call.from_user.id, row["game"], bet, pot)


async def run_duel(call: CallbackQuery, duel_id: int, creator_id: int, opponent_id: int, game: str, bet: float, pot: float):
    bot = call.bot

    # Сообщаем о старте
    try:
        await bot.send_message(
            creator_id,
            "⚔️ Соперник найден! Бросаем…" if (await db.get_user_lang(creator_id)) == "ru" else "⚔️ Opponent found! Rolling…",
        )
    except Exception:
        pass

    try:
        await bot.send_message(
            opponent_id,
            "⚔️ Дуэль началась! Бросаем…" if (await db.get_user_lang(opponent_id)) == "ru" else "⚔️ Duel started! Rolling…",
        )
    except Exception:
        pass

    emoji = game_emoji(game)

    async def roll(user_id: int):
        msg = await bot.send_dice(user_id, emoji=emoji)
        await asyncio.sleep(3.2)
        return msg.dice.value

    rolls = []
    for _ in range(3):
        c_val = await roll(creator_id)
        o_val = await roll(opponent_id)
        rolls.append((c_val, o_val))
        if c_val != o_val:
            break

    c_val, o_val = rolls[-1]
    if c_val == o_val:
        winner_id = random.choice([creator_id, opponent_id])
    else:
        winner_id = creator_id if c_val > o_val else opponent_id

    await db.finish_duel(duel_id, winner_id)
    await change_balance(
        winner_id,
        pot,
        tx_type="duel_win",
        meta={"duel_id": duel_id, "rolls": rolls, "game": game},
    )

    def fmt(lang_local: str, win: bool, your: int, opp: int):
        if lang_local == "ru":
            return (
                f"{'🎉 Победа!' if win else '❌ Поражение.'}\n"
                f"Игра: {'Кубик' if game == 'dice' else 'Рулетка 🎯'}\n"
                f"Ваш бросок: {your} | Оппонент: {opp}\n"
                f"Банк: {pot:.2f}$"
            )
        return (
            f"{'🎉 You win!' if win else '❌ You lose.'}\n"
            f"Game: {'Dice' if game == 'dice' else 'Darts 🎯'}\n"
            f"Your roll: {your} | Opponent: {opp}\n"
            f"Pot: {pot:.2f}$"
        )

    creator_lang = await db.get_user_lang(creator_id)
    opponent_lang = await db.get_user_lang(opponent_id)

    try:
        await bot.send_message(
            creator_id,
            fmt(creator_lang, winner_id == creator_id, c_val, o_val),
        )
    except Exception:
        pass

    try:
        await bot.send_message(
            opponent_id,
            fmt(opponent_lang, winner_id == opponent_id, o_val, c_val),
        )
    except Exception:
        pass

    await call.message.edit_text(
        "Дуэль сыграна! Проверяй результат в личке." if (await db.get_user_lang(call.from_user.id)) == "ru" else "Duel played! Check your chat for the result.",
        reply_markup=duel_bets_keyboard(await db.get_user_lang(call.from_user.id)),
    )

    loser_id = opponent_id if winner_id == creator_id else creator_id
    await send_duel_log(
        bot,
        f"🏁 Duel #{duel_id} finished | Game: {game} | Bet: {bet:.2f}$ | Pot: {pot:.2f}$ | Winner: {winner_id} | Loser: {loser_id} | Rolls: {rolls}",
    )
    await award_loss_commission(loser_id, bet)


def game_emoji(game: str) -> str:
    return {
        "dice": "🎲",
        "darts": "🎯",
        "football": "⚽️",
        "basketball": "🏀",
        "bowling": "🎳",
    }.get(game, "🎲")


def game_title(game: str, lang: str) -> str:
    titles = {
        "dice": ("Кубик", "Dice"),
        "darts": ("Дартс", "Darts"),
        "football": ("Футбол", "Football"),
        "basketball": ("Баскетбол", "Basketball"),
        "bowling": ("Боулинг", "Bowling"),
    }
    ru, en = titles.get(game, ("Кубик", "Dice"))
    return ru if lang == "ru" else en


async def send_duel_log(bot, text: str):
    channel = await get_duel_log_channel()
    if not channel:
        return
    try:
        await bot.send_message(channel, text, disable_web_page_preview=True)
    except Exception:
        pass
