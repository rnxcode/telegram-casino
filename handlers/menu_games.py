from aiogram import Router, F
from aiogram.types import CallbackQuery
from keyboards.games_menu import games_menu

router = Router()

@router.callback_query(F.data == "games_menu")
async def open_games_menu(call: CallbackQuery, lang: str):

    if lang == "ru":
        text = (
            "🎮 <b>Игры</b>\n"
            "Выбери режим:\n\n"
            "• 🎲 Dice | 💣 Мины | 🔫 Русская рулетка\n"
            "• 🃏 Блэкджек | 🎰 Рулетка\n"
            "• ⚽️ Футбол | 🎯 Дартс | 🏀 Баскет | 🎳 Боулинг\n\n"
            "Нажми кнопку ниже:"
        )
    else:
        text = (
            "🎮 <b>Games</b>\n"
            "Pick a mode:\n\n"
            "• 🎲 Dice | 💣 Mines | 🔫 Russian roulette\n"
            "• 🃏 Blackjack | 🎰 Roulette\n"
            "• ⚽️ Football | 🎯 Darts | 🏀 Basketball | 🎳 Bowling\n\n"
            "Tap a button below:"
        )

    await call.message.edit_text(text, reply_markup=games_menu(lang))
