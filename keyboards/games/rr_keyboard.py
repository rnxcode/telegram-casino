from aiogram.utils.keyboard import InlineKeyboardBuilder

def rr_keyboard(lang: str, stage: int):
    t = {
        "ru": {
            "shoot": "🔫 Выстрел",
            "take": "🛑 Забрать",
            "bet": "💰 Изменить ставку",
            "back": "⬅️ Назад"
        },
        "en": {
            "shoot": "🔫 Shoot",
            "take": "🛑 Take",
            "bet": "💰 Change bet",
            "back": "⬅️ Back"
        }
    }[lang]

    kb = InlineKeyboardBuilder()

    kb.button(text=t["shoot"], callback_data=f"rr_shoot_{stage}")
    kb.button(text=t["take"], callback_data=f"rr_take_{stage}")
    kb.button(text=t["bet"], callback_data="rr_change_bet")
    kb.button(text=t["back"], callback_data="games_menu")

    kb.adjust(1, 1, 1, 1)
    return kb.as_markup()
