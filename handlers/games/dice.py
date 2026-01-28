# handlers/games/dice.py
import random
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.menu import main_menu
from services.balance import get_balance, change_balance
from services.referrals import award_loss_commission
from services.game_stats import log_dice_game

router = Router()


class DiceState(StatesGroup):
    waiting_bet = State()
    waiting_choice = State()


# -------------------------------
# Кнопки
# -------------------------------
def bet_keyboard(lang: str):
    kb = InlineKeyboardBuilder()
    buttons = [1, 5, 10, 30, 50, 100]

    for chunk in [buttons[i:i+3] for i in range(0, len(buttons), 3)]:
        kb.row(*[
            InlineKeyboardButton(text=f"{x}$", callback_data=f"dice_bet_{x}")
            for x in chunk
        ])

    kb.row(InlineKeyboardButton(
        text="⬅️ Назад" if lang == "ru" else "⬅️ Back",
        callback_data="games_menu"))
    return kb.as_markup()


def choice_keyboard(lang: str):
    kb = InlineKeyboardBuilder()

    if lang == "ru":
        kb.row(
            InlineKeyboardButton(text="🎯 Число", callback_data="dc_number"),
            InlineKeyboardButton(text="⚡ Чёт/Нечёт", callback_data="dc_even")
        )
    else:
        kb.row(
            InlineKeyboardButton(text="🎯 Number", callback_data="dc_number"),
            InlineKeyboardButton(text="⚡ Even/Odd", callback_data="dc_even")
        )

    kb.row(InlineKeyboardButton(
        text="⬅️ Назад" if lang == "ru" else "⬅️ Back",
        callback_data="games_menu"))
    return kb.as_markup()


def number_choice_keyboard():
    kb = InlineKeyboardBuilder()
    for i in range(1, 7):
        kb.add(InlineKeyboardButton(text=str(i), callback_data=f"dc_n_{i}"))
    kb.adjust(3)
    return kb.as_markup()


# -------------------------------
# Старт
# -------------------------------
@router.callback_query(F.data == "game_dice")
async def start_dice(call: CallbackQuery, state: FSMContext, lang: str):
    user_id = call.from_user.id
    balance = await get_balance(user_id)

    if balance < 1:
        return await call.answer(
            "Недостаточно средств" if lang == "ru" else "Not enough balance",
            show_alert=True
        )

    await state.set_state(DiceState.waiting_bet)

    await call.message.edit_text(
        "Выбери ставку:" if lang == "ru" else "Choose your bet:",
        reply_markup=bet_keyboard(lang)
    )


# -------------------------------
# Установка ставки
# -------------------------------
@router.callback_query(F.data.startswith("dice_bet_"), DiceState.waiting_bet)
async def set_bet(call: CallbackQuery, state: FSMContext, lang: str):
    bet = float(call.data.split("_")[2])
    user_id = call.from_user.id

    if await get_balance(user_id) < bet:
        return await call.answer("Недостаточно средств" if lang == "ru" else "Not enough balance", show_alert=True)

    await state.update_data(bet=bet)
    await state.set_state(DiceState.waiting_choice)

    await call.message.edit_text(
        "Выбери режим игры:" if lang == "ru" else "Choose mode:",
        reply_markup=choice_keyboard(lang)
    )


# -------------------------------
# Выбор режима
# -------------------------------
@router.callback_query(F.data == "dc_even", DiceState.waiting_choice)
async def choose_even_odd(call: CallbackQuery, state: FSMContext, lang: str):
    kb = InlineKeyboardBuilder()
    if lang == "ru":
        kb.row(
            InlineKeyboardButton(text="🔵 Чёт", callback_data="dc_even_even"),
            InlineKeyboardButton(text="🔴 Нечёт", callback_data="dc_even_odd")
        )
    else:
        kb.row(
            InlineKeyboardButton(text="🔵 Even", callback_data="dc_even_even"),
            InlineKeyboardButton(text="🔴 Odd", callback_data="dc_even_odd")
        )
    await call.message.edit_text(
        "Выберите:" if lang == "ru" else "Choose:",
        reply_markup=kb.as_markup()
    )


@router.callback_query(F.data == "dc_number", DiceState.waiting_choice)
async def choose_number(call: CallbackQuery, state: FSMContext, lang: str):
    await call.message.edit_text(
        "Выбери число:" if lang == "ru" else "Pick a number:",
        reply_markup=number_choice_keyboard()
    )


# -------------------------------
# Игра
# -------------------------------
import asyncio

async def do_roll(message, bet, user_id, username, check_win, choice, lang, multiplier=None):
    # списываем ставку
    await change_balance(user_id, -bet)

    # отправляем кубик
    dice_msg = await message.answer_dice(emoji="🎲")

    # Telegram всегда крутит анимацию ровно ~3.2 секунды
    await asyncio.sleep(3.2)

    value = dice_msg.dice.value
    won = check_win(value)
    win_amount = (bet * multiplier) if won and multiplier else (bet * 2 if won else 0)

    if won:
        await change_balance(user_id, win_amount)
    else:
        await award_loss_commission(user_id, bet)

    # логирование
    await log_dice_game(
        user_id=user_id,
        bet=bet,
        win=win_amount,
        result="win" if won else "lose",
        username=username,
        multiplier=multiplier
    )

    # вывод результата игроку
    result_text = (
        f"🎲 Выпало: {value}\n"
        f"{'🎉 Победа!' if won else '❌ Проигрыш'}\n"
        f"💰 Выигрыш: {win_amount}$"
    )

    await message.answer(result_text)



# -------------------------------
# Обработка выбора
# -------------------------------
@router.callback_query(F.data.startswith("dc_even_"), DiceState.waiting_choice)
async def play_even(call: CallbackQuery, state: FSMContext, lang: str):
    data = await state.get_data()
    bet = data["bet"]
    user_id = call.from_user.id
    username = call.from_user.username

    even = call.data.endswith("even")   # True если выбрали "чет"

    await state.clear()

    await do_roll(
        message=call.message,
        bet=bet,
        user_id=user_id,
        username=username,
        check_win=lambda r: (r % 2 == 0) == even,
        choice="even" if even else "odd",
        lang=lang,
        multiplier=2
    )



@router.callback_query(F.data.startswith("dc_n_"), DiceState.waiting_choice)
async def play_number(call: CallbackQuery, state: FSMContext, lang: str):
    data = await state.get_data()
    bet = data["bet"]
    user_id = call.from_user.id
    username = call.from_user.username

    number = int(call.data.split("_")[2])

    await state.clear()

    await do_roll(
        message=call.message,
        bet=bet,
        user_id=user_id,
        username=username,
        check_win=lambda r: r == number,
        choice=str(number),
        lang=lang,
        multiplier=6
    )



# -------------------------------
# Exit
# -------------------------------
@router.callback_query(F.data == "dice_exit")
async def dice_exit(call: CallbackQuery, state: FSMContext, lang: str):
    await state.clear()
    await call.message.edit_text(
        "🎮 Выбор игр" if lang == "ru" else "🎮 Games",
        reply_markup=games_menu(lang)
    )
