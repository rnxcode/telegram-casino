from aiogram.utils.keyboard import InlineKeyboardBuilder

def deposit_keyboard(lang: str):
    t = {
        "ru": {
            "crypto": "💳 Crypto",
            "rocket": "🚀 Rocket",
            "stars": "⭐ Stars",
            "back": "⬅️ Назад"
        },
        "en": {
            "crypto": "💳 Crypto",
            "rocket": "🚀 Rocket",
            "stars": "⭐ Stars",
            "back": "⬅️ Back"
        }
    }[lang]

    kb = InlineKeyboardBuilder()
    kb.button(text=t["crypto"], callback_data="dep_crypto")
    kb.button(text=t["rocket"], callback_data="dep_rocket")
    kb.button(text=t["stars"], callback_data="dep_stars")
    kb.button(text=t["back"], callback_data="dep_back")
    kb.adjust(2, 2)
    return kb.as_markup()
from aiogram.utils.keyboard import InlineKeyboardBuilder

def crypto_check_keyboard(invoice_id: str, lang: str):
    t = {
        "ru": {
            "check": "🔄 Проверить оплату",
            "cancel": "⛔ Отмена"
        },
        "en": {
            "check": "🔄 Check payment",
            "cancel": "⛔ Cancel"
        }
    }[lang]

    kb = InlineKeyboardBuilder()
    kb.button(text=t["check"], callback_data=f"crypto_check:{invoice_id}")
    kb.button(text=t["cancel"], callback_data="dep_back")
    kb.adjust(1)
    return kb.as_markup()
