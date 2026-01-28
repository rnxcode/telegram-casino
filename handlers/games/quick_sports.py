import asyncio
from decimal import Decimal

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.balance import change_balance, get_balance
from services.referrals import award_loss_commission
from keyboards.menu import main_menu

router = Router()


SPORTS = {
    "football": {"emoji": "⚽️", "win_min": 4},
    "darts": {"emoji": "🎯", "win_min": 4},
    "basketball": {"emoji": "🏀", "win_min": 4},
    "bowling": {"emoji": "🎳", "win_min": 4},
}


def sport_bet_keyboard(game: str, lang: str):
    kb = InlineKeyboardBuilder()
    amounts = [1, 5, 10, 20, 50, 100]
    for chunk in [amounts[i : i + 3] for i in range(0, len(amounts), 3)]:
        kb.row(
            *[
                InlineKeyboardButton(
                    text=f"{amt}$",
                    callback_data=f"sport_bet:{game}:{amt}",
                )
                for amt in chunk
            ]
        )
    kb.row(InlineKeyboardButton(text="⬅️ Назад" if lang == "ru" else "⬅️ Back", callback_data="games_menu"))
    return kb.as_markup()


SPORT_CALLBACKS = {
    "game_football",
    "game_darts",
    "game_basketball",
    "game_bowling",
}


@router.callback_query(F.data.in_(SPORT_CALLBACKS))
async def choose_sport(call: CallbackQuery, lang: str):
    game = call.data.split("_", 1)[1]
    if game not in SPORTS:
        return
    title = sport_title(game, lang)
    text = (
        f"{title}\n\n"
        "Выбери ставку и бросай. Значение 4+ — победа, получаешь x2."
        if lang == "ru"
        else f"{title}\n\nPick a stake. Roll 4+ to win x2."
    )
    await call.message.edit_text(text, reply_markup=sport_bet_keyboard(game, lang))


@router.callback_query(F.data.startswith("sport_bet:"))
async def start_sport(call: CallbackQuery, lang: str):
    _, game, amt_raw = call.data.split(":")
    if game not in SPORTS:
        return
    bet = float(Decimal(amt_raw))
    user_id = call.from_user.id

    if await get_balance(user_id) < bet:
        return await call.answer("Недостаточно средств" if lang == "ru" else "Not enough balance", show_alert=True)

    await change_balance(user_id, -bet, tx_type="sport_bet", meta={"game": game})

    emoji = SPORTS[game]["emoji"]
    dice_msg = await call.message.answer_dice(emoji=emoji)
    await asyncio.sleep(3.2)
    value = dice_msg.dice.value

    win = value >= SPORTS[game]["win_min"]
    win_amount = bet * 2 if win else 0
    if win:
        await change_balance(user_id, win_amount, tx_type="sport_win", meta={"game": game, "roll": value})
    else:
        await award_loss_commission(user_id, bet)

    result = (
        f"{'🎉 Победа!' if win else '❌ Проигрыш.'}\n"
        f"Бросок: {value}\n"
        f"{'Получено' if win else 'Потеря'}: {win_amount if win else bet:.2f}$"
        if lang == "ru"
        else f"{'🎉 Win!' if win else '❌ Lose.'}\nRoll: {value}\n{'Earned' if win else 'Lost'}: {win_amount if win else bet:.2f}$"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎮 Ещё" if lang == "ru" else "🎮 Again", callback_data=f"game_{game}")],
            [InlineKeyboardButton(text="⬅️ Назад" if lang == "ru" else "⬅️ Back", callback_data="games_menu")],
        ]
    )
    await call.message.answer(result, reply_markup=kb)


def sport_title(game: str, lang: str) -> str:
    names = {
        "football": ("⚽️ Футбол", "⚽️ Football"),
        "darts": ("🎯 Дартс", "🎯 Darts"),
        "basketball": ("🏀 Баскетбол", "🏀 Basketball"),
        "bowling": ("🎳 Боулинг", "🎳 Bowling"),
    }
    ru, en = names.get(game, ("🎲 Игра", "🎲 Game"))
    return ru if lang == "ru" else en
