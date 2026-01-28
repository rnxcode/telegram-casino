from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

def rr_bets_keyboard(lang: str):
    kb = InlineKeyboardBuilder()

    # Ставки
    for bet in [1, 5, 10, 30, 50, 100]:
        kb.button(text=f"{bet} $", callback_data=f"rr_set_bet_{bet}")

    kb.adjust(2)

    # Кнопка назад
    kb.row(
        InlineKeyboardButton(
            text="⬅️ Назад" if lang == "ru" else "⬅️ Back",
            callback_data="rr_back"
        )
    )

    return kb.as_markup()
