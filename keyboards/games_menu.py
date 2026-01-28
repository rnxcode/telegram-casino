from aiogram.utils.keyboard import InlineKeyboardBuilder

def games_menu(lang: str):

    t = {
        "ru": {
            "rr": "🔫 Русская рулетка",
            "dice": "🎲 Dice",
            "football": "⚽️ Футбол",
            "darts": "🎯 Дартс",
            "basketball": "🏀 Баскетбол",
            "bowling": "🎳 Боулинг",
            "roulette": "🎰 Рулетка",
            "mines": "💣 Мины",
            "bj": "🃏 Блэкджек",
            "back": "⬅ Назад"
        },
        "en": {
            "rr": "🔫 Russian Roulette",
            "dice": "🎲 Dice",
            "football": "⚽️ Football",
            "darts": "🎯 Darts",
            "basketball": "🏀 Basketball",
            "bowling": "🎳 Bowling",
            "roulette": "🎰 Roulette",
            "mines": "💣 Mines",
            "bj": "🃏 Blackjack",
            "back": "⬅ Back"
        }
    }[lang]

    kb = InlineKeyboardBuilder()

    kb.button(text=t["dice"], callback_data="game_dice")
    kb.button(text=t["mines"], callback_data="game_mines")
    kb.button(text=t["rr"], callback_data="game_russian")
    kb.button(text=t["bj"], callback_data="game_blackjack")
    kb.button(text=t["roulette"], callback_data="game_roulette")
    kb.button(text=t["football"], callback_data="game_football")
    kb.button(text=t["darts"], callback_data="game_darts")
    kb.button(text=t["basketball"], callback_data="game_basketball")
    kb.button(text=t["bowling"], callback_data="game_bowling")
    kb.button(text=t["back"], callback_data="back")

    kb.adjust(2, 2, 2, 2, 1)
    return kb.as_markup()
