import asyncio
import random
from decimal import Decimal

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.balance import change_balance, get_balance
from services.referrals import award_loss_commission
from services.game_stats import log_roulette_game


router = Router()


def roulette_bets_keyboard(lang: str):
    kb = InlineKeyboardBuilder()
    amounts = [1, 5, 10, 25, 50, 100]
    for chunk in [amounts[i : i + 3] for i in range(0, len(amounts), 3)]:
        kb.row(
            *[
                InlineKeyboardButton(text=f"{amt}$", callback_data=f"roul_bet:{amt}")
                for amt in chunk
            ]
        )
    kb.row(
        InlineKeyboardButton(text="⬅️ Назад" if lang == "ru" else "⬅️ Back", callback_data="games_menu")
    )
    return kb.as_markup()


@router.callback_query(F.data == "game_roulette")
async def open_roulette(call: CallbackQuery, lang: str):
    text = (
        "🎰 <b>Рулетка</b>\n"
        "Выберите ставку, крутим слоты.\n"
        "Выпало 50+ → x2, иначе проигрыш."
    ) if lang == "ru" else (
        "🎰 <b>Roulette</b>\n"
        "Pick a stake and spin.\n"
        "Roll 50+ to win x2, otherwise you lose."
    )
    await call.message.edit_text(text, reply_markup=roulette_bets_keyboard(lang))


@router.callback_query(F.data.startswith("roul_bet:"))
async def play_roulette(call: CallbackQuery, lang: str):
    bet = float(Decimal(call.data.split(":")[1]))
    user_id = call.from_user.id

    if await get_balance(user_id) < bet:
        return await call.answer(
            "Недостаточно средств. Пополните или выберите меньшую ставку."
            if lang == "ru"
            else "Not enough balance. Top up or pick a smaller stake.",
            show_alert=True,
        )

    await change_balance(user_id, -bet)

    roll_msg = await call.message.answer_dice(emoji="🎰")
    await asyncio.sleep(3.2)
    value = roll_msg.dice.value  # 1..64 for slots

    win = value >= 50
    win_amount = bet * 2 if win else 0
    if win:
        await change_balance(user_id, win_amount)
    else:
        await award_loss_commission(user_id, bet)

    await log_roulette_game(user_id, bet, win_amount, "win" if win else "lose", call.from_user.username)

    if lang == "ru":
        result_text = (
            f"🎰 Выпало: {value}\n"
            f"{'🎉 Победа' if win else '❌ Проигрыш'}\n"
            f"{'Выигрыш' if win else 'Потеря'}: {win_amount if win else bet:.2f}$"
        )
    else:
        result_text = (
            f"🎰 Rolled: {value}\n"
            f"{'🎉 Win' if win else '❌ Lose'}\n"
            f"{'Payout' if win else 'Lost'}: {win_amount if win else bet:.2f}$"
        )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎰 Ещё" if lang == "ru" else "🎰 Again", callback_data="game_roulette")],
            [InlineKeyboardButton(text="⬅️ Назад" if lang == "ru" else "⬅️ Back", callback_data="games_menu")],
        ]
    )
    await call.message.answer(result_text, reply_markup=kb)
