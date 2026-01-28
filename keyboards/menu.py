# keyboards/menu.py - обновлённое главное меню с дуэлями и розыгрышами
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

_bot_username: str | None = None
_support_url: str | None = None


def set_bot_username(username: str | None) -> None:
    global _bot_username
    _bot_username = username


def get_bot_username() -> str | None:
    return _bot_username


def set_support_url(url: str | None) -> None:
    global _support_url
    _support_url = url


def await_support_url() -> str | None:
    return _support_url


def main_menu(lang: str):
    t = {
        "ru": {
            "games": "🎮 Игры",
            "duels": "⚔️ Дуэли",
            "raffle": "🎁 Розыгрыш",
            "support": "🛟 Поддержка",
            "profile": "👤 Профиль",
            "ref": "👥 Рефералы",
            "language": "🌐 Сменить язык",
            "add_chat": "➕ Добавить в чат",
        },
        "en": {
            "games": "🎮 Games",
            "duels": "⚔️ Duels",
            "raffle": "🎁 Raffle",
            "support": "🛟 Support",
            "profile": "👤 Profile",
            "ref": "👥 Referrals",
            "language": "🌐 Change language",
            "add_chat": "➕ Add bot to chat",
        }
    }[lang]

    add_chat_url = f"https://t.me/{_bot_username}?startgroup=true" if _bot_username else None
    support_url = await_support_url()

    kb = InlineKeyboardBuilder()
    # Пирамидальная сетка
    kb.row(InlineKeyboardButton(text=t["games"], callback_data="games_menu"))
    kb.row(
        InlineKeyboardButton(text=t["duels"], callback_data="duels"),
        InlineKeyboardButton(text=t["raffle"], callback_data="raffle"),
    )
    kb.row(
        InlineKeyboardButton(text=t["profile"], callback_data="profile"),
        InlineKeyboardButton(text=t["ref"], callback_data="ref_menu"),
        InlineKeyboardButton(text=t["language"], callback_data="change_language"),
    )
    # Ссылки отдельной линией
    link_buttons = []
    if add_chat_url:
        link_buttons.append(InlineKeyboardButton(text=t["add_chat"], url=add_chat_url))
    if support_url:
        link_buttons.append(InlineKeyboardButton(text=t["support"], url=support_url))
    info_url = "https://telegra.ph/LudoTons-Casino--tvoj-bilet-v-mir-azarta-i-bolshih-vyigryshej-12-11"
    if link_buttons:
        kb.row(*link_buttons)
    kb.row(
        InlineKeyboardButton(
            text="ℹ️ Информация" if lang == "ru" else "ℹ️ Info",
            url=info_url,
        )
    )
    return kb.as_markup()


def back_btn(lang: str = "ru"):
    kb = InlineKeyboardBuilder()
    text = "⬅️ Назад" if lang == "ru" else "⬅️ Back"
    kb.button(text=text, callback_data="back")
    return kb.as_markup()
