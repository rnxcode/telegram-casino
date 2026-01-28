from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.menu import get_bot_username


def duel_bets_keyboard(lang: str):
    kb = InlineKeyboardBuilder()
    amounts = [1, 5, 10, 25, 50, 100]
    for chunk in [amounts[i : i + 3] for i in range(0, len(amounts), 3)]:
        kb.row(
            *[
                InlineKeyboardButton(
                    text=f"{amount}$",
                    callback_data=f"duel_bet:{amount}",
                )
                for amount in chunk
            ]
        )

    kb.row(
        InlineKeyboardButton(
            text="⬅️ В меню" if lang == "ru" else "⬅️ Menu",
            callback_data="back",
        )
    )
    return kb.as_markup()


def duel_game_keyboard(bet: float, lang: str):
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(
            text="🎲 Кубик" if lang == "ru" else "🎲 Dice",
            callback_data=f"duel_game:{bet}:dice",
        ),
        InlineKeyboardButton(
            text="🎯 Дартс" if lang == "ru" else "🎯 Darts",
            callback_data=f"duel_game:{bet}:darts",
        ),
    )
    kb.row(
        InlineKeyboardButton(
            text="⚽️ Футбол" if lang == "ru" else "⚽️ Football",
            callback_data=f"duel_game:{bet}:football",
        ),
        InlineKeyboardButton(
            text="🏀 Баскетбол" if lang == "ru" else "🏀 Basketball",
            callback_data=f"duel_game:{bet}:basketball",
        ),
    )
    kb.row(
        InlineKeyboardButton(
            text="🎳 Боулинг" if lang == "ru" else "🎳 Bowling",
            callback_data=f"duel_game:{bet}:bowling",
        ),
    )
    kb.row(
        InlineKeyboardButton(
            text="⬅️ Назад" if lang == "ru" else "⬅️ Back",
            callback_data="duels",
        )
    )
    return kb.as_markup()


def duel_wait_keyboard(duel_id: int, lang: str):
    kb = InlineKeyboardBuilder()
    username = get_bot_username()
    if username:
        kb.row(
            InlineKeyboardButton(
                text="🔗 Поделиться дуэлью" if lang == "ru" else "🔗 Share duel",
                url=f"https://t.me/{username}?start=duel_{duel_id}",
            )
        )
    kb.row(
        InlineKeyboardButton(
            text="❌ Отменить дуэль" if lang == "ru" else "❌ Cancel duel",
            callback_data=f"duel_cancel:{duel_id}",
        )
    )
    kb.row(
        InlineKeyboardButton(
            text="⬅️ Меню" if lang == "ru" else "⬅️ Menu",
            callback_data="back",
        )
    )
    return kb.as_markup()
