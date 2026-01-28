import asyncio
from aiogram import Router, F
from aiogram.types import CallbackQuery

from keyboards.games.rr_keyboard import rr_keyboard
from keyboards.menu import main_menu
from keyboards.games_menu import games_menu
from .rr_bets import rr_bets_keyboard
from services.balance import get_balance, change_balance
from services.games.rr_logic import rr_shoot, rr_win
from services.referrals import award_loss_commission

router = Router()
active_rr = {}  # user_id → {"bet": int, "stage": int}


# ================================
#  АНИМАЦИИ СИМВОЛОВ ● ○ (красиво и современно)
# ================================

async def rr_spin(message, lang):
    """Вращение барабана — 6 позиций по кругу"""
    frames = [
        "[ ● ○ ○ ○ ○ ○ ]",
        "[ ○ ● ○ ○ ○ ○ ]",
        "[ ○ ○ ● ○ ○ ○ ]",
        "[ ○ ○ ○ ● ○ ○ ]",
        "[ ○ ○ ○ ○ ● ○ ]",
        "[ ○ ○ ○ ○ ○ ● ]",
    ]
    title = "Вращаем барабан..." if lang == "ru" else "Spinning..."

    for f in frames:
        await message.edit_text(f"{title}\n\n{f}")
        await asyncio.sleep(0.12)


async def rr_click(message, lang):
    """Пустой выстрел — красивый ‘щёлк’"""
    if lang == "ru":
        frames = [
            "[ ● ]\n🔫 ЩЕЛК...",
            "[ ○ ]\n🙂 Пусто!"
        ]
    else:
        frames = [
            "[ ● ]\n🔫 CLICK...",
            "[ ○ ]\n🙂 Empty!"
        ]

    for f in frames:
        await message.edit_text(f)
        await asyncio.sleep(0.22)


async def rr_boom(message, lang):
    """Выстрел — усиленная анимация"""
    frames = [
        "[ ● ]",
        "💥",
        "💥💥",
        "💥💥💥",
        "💀 BOOM!" if lang == "en" else "💀 БА-БАХ!"
    ]
    for f in frames:
        await message.edit_text(f)
        await asyncio.sleep(0.18)


# ================================
#  ТЕКСТЫ (современные, но без ASCII рамок)
# ================================
def rr_text(lang, bet, stage):
    mult = {1: "1.2x", 2: "1.5x", 3: "2.0x", 4: "2.8x", 5: "4.0x"}[stage]

    if lang == "ru":
        return (
            f"<b>🔫 Русская рулетка</b>\n\n"
            f"💵 Ставка: <b>{bet}$</b>\n"
            f"📈 Этап: <b>{stage}/5</b>\n"
            f"🔥 Множитель: <b>{mult}</b>\n\n"
            "Нажмите «Стрелять»."
        )
    else:
        return (
            f"<b>🔫 Russian Roulette</b>\n\n"
            f"💵 Bet: <b>{bet}$</b>\n"
            f"📈 Stage: <b>{stage}/5</b>\n"
            f"🔥 Multiplier: <b>{mult}</b>\n\n"
            "Press Shoot."
        )


def rr_dead(lang):
    return "💀 Пуля. Вы проиграли." if lang == "ru" else "💀 Bullet. You died."


def rr_victory(lang, win):
    return (
        f"🏆 Победа!\nЗабрал: <b>{win}$</b>"
        if lang == "ru"
        else f"🏆 Victory!\nTaken: <b>{win}$</b>"
    )


def rr_bet_text(lang):
    if lang == "ru":
        return (
            "<b>💵 Выберите ставку</b>\n\n"
            "1$ 5$ 10$\n"
            "30$ 50$ 100$\n\n"
            "Введите или нажмите кнопку:"
        )
    else:
        return (
            "<b>💵 Choose bet</b>\n\n"
            "1$ 5$ 10$\n"
            "30$ 50$ 100$\n\n"
            "Enter or press button:"
        )

# -------------------------------
# Back to games
# -------------------------------
def games_menu_text(lang: str) -> str:
    if lang == "ru":
        return (
            "🎮 <b>Игры</b>\n"
            "Выбери режим:\n\n"
            "• 🎲 Dice | 💣 Мины | 🔫 Русская рулетка\n"
            "• 🃏 Блэкджек | 🎰 Рулетка | 🧱 Башня\n"
            "• ⚽️ Футбол | 🎯 Дартс | 🏀 Баскет | 🎳 Боулинг\n\n"
            "Нажми кнопку ниже:"
        )
    return (
        "🎮 <b>Games</b>\n"
        "Pick a mode:\n\n"
        "• 🎲 Dice | 💣 Mines | 🔫 Russian roulette\n"
        "• 🃏 Blackjack | 🎰 Roulette | 🧱 Tower\n"
        "• ⚽️ Football | 🎯 Darts | 🏀 Basketball | 🎳 Bowling\n\n"
        "Tap a button below:"
    )

# ================================
#  ХЕНДЛЕРЫ
# ================================
@router.callback_query(F.data == "game_russian")
async def rr_start_game(call: CallbackQuery, lang: str):
    await call.message.edit_text(
        rr_bet_text(lang),
        reply_markup=rr_bets_keyboard(lang)
    )


@router.callback_query(F.data == "rr_back")
async def rr_back(call: CallbackQuery, lang: str):
    await call.message.edit_text(games_menu_text(lang), reply_markup=games_menu(lang))


@router.callback_query(F.data.startswith("rr_set_bet_"))
async def rr_set_bet(call: CallbackQuery, lang: str):
    user = call.from_user.id
    bet = int(call.data.split("_")[-1])

    balance = await get_balance(user)
    if balance < bet:
        await call.answer(
            "❌ Недостаточно средств. Пополните или выберите меньшую ставку."
            if lang == "ru"
            else "❌ Not enough balance. Top up or choose a smaller bet.",
            show_alert=True,
        )
        return await call.message.edit_text(rr_bet_text(lang), reply_markup=rr_bets_keyboard(lang))

    await change_balance(user, -bet)

    active_rr[user] = {"bet": bet, "stage": 1}

    await call.message.edit_text(
        rr_text(lang, bet, 1),
        reply_markup=rr_keyboard(lang, 1)
    )


@router.callback_query(F.data.startswith("rr_shoot_"))
async def rr_shoot_stage(call: CallbackQuery, lang: str):
    user = call.from_user.id
    game = active_rr.get(user)

    if not game:
        return await call.answer("Ошибка" if lang=="ru" else "Error")

    bet = game["bet"]
    stage = game["stage"]

    # 1) вращаем барабан
    await rr_spin(call.message, lang)
    await asyncio.sleep(0.25)

    # 2) определяем – смерть?
    dead = rr_shoot(stage)

    if dead:
        # проигрышная анимация
        await rr_boom(call.message, lang)

        from services.game_stats import log_rr_game
        await log_rr_game(user, bet, stage, 0, "lose")
        await award_loss_commission(user, bet)

        del active_rr[user]
        return await call.message.edit_text(
            rr_dead(lang),
            reply_markup=main_menu(lang)
        )

    # 3) выжил
    await rr_click(call.message, lang)

    game["stage"] += 1

    if game["stage"] > 5:
        win = rr_win(bet, 5)
        await change_balance(user, win)

        from services.game_stats import log_rr_game
        await log_rr_game(user, bet, 5, win, "win")

        del active_rr[user]
        return await call.message.edit_text(
            rr_victory(lang, win),
            reply_markup=main_menu(lang)
        )

    await call.message.edit_text(
        rr_text(lang, bet, game["stage"]),
        reply_markup=rr_keyboard(lang, game["stage"])
    )


@router.callback_query(F.data == "rr_change_bet")
async def rr_change_bet(call: CallbackQuery, lang: str):
    user = call.from_user.id
    game = active_rr.get(user)

    if game:
        await change_balance(user, game["bet"])
        del active_rr[user]

    await call.message.edit_text(rr_bet_text(lang), reply_markup=rr_bets_keyboard(lang))


@router.callback_query(F.data.startswith("rr_take_"))
async def rr_take(call: CallbackQuery, lang: str):
    user = call.from_user.id
    game = active_rr.get(user)

    if not game:
        return await call.answer("Ошибка" if lang == "ru" else "Error")

    bet = game["bet"]
    stage = game["stage"]

    win = rr_win(bet, max(stage - 1, 0))
    await change_balance(user, bet + win)

    from services.game_stats import log_rr_game
    await log_rr_game(user, bet, stage, win, "take")

    del active_rr[user]

    msg = (
        f"🏆 Забрал: {win}$ (этап {stage})"
        if lang == "ru" else
        f"🏆 Taken: {win}$ (stage {stage})"
    )

    await call.message.edit_text(msg, reply_markup=main_menu(lang))
