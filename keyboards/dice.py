from aiogram.utils.keyboard import InlineKeyboardBuilder

def dice_menu(lang: str):
    t = {
        "ru": {
            "over": "⬆️ Больше (4–6)",
            "under": "⬇️ Меньше (1–3)",
            "even": "⚪ Чёт",
            "odd": "⚫ Нечёт",
            "choose": "🎯 Число",
        },
        "en": {
            "over": "⬆️ Over (4–6)",
            "under": "⬇️ Under (1–3)",
            "even": "⚪ Even",
            "odd": "⚫ Odd",
            "choose": "🎯 Number",
        }
    }[lang]

    kb = InlineKeyboardBuilder()
    kb.button(text=t["over"], callback_data="dice_over")
    kb.button(text=t["under"], callback_data="dice_under")
    kb.button(text=t["even"], callback_data="dice_even")
    kb.button(text=t["odd"], callback_data="dice_odd")

    for i in range(1, 7):
        kb.button(text=f"{i}", callback_data=f"dice_num{i}")

    kb.adjust(2, 2, 6)
    return kb.as_markup()
