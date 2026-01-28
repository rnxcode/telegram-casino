# keyboards/language.py - клавиатура выбора языка
from aiogram.utils.keyboard import InlineKeyboardBuilder

def language_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="🇷🇺 Русский", callback_data="lang_ru")
    kb.button(text="🇬🇧 English", callback_data="lang_en")
    kb.adjust(2)
    return kb.as_markup()

