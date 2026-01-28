from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def raffle_menu_keyboard(lang: str):
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(
            text="🎁 Создать розыгрыш" if lang == "ru" else "🎁 Create raffle",
            callback_data="raffle_create",
        )
    )
    kb.row(
        InlineKeyboardButton(
            text="⬅️ Меню" if lang == "ru" else "⬅️ Menu",
            callback_data="back",
        )
    )
    return kb.as_markup()


def raffle_amounts_keyboard(lang: str):
    kb = InlineKeyboardBuilder()
    amounts = [1, 5, 10, 20, 50, 100]
    for chunk in [amounts[i : i + 3] for i in range(0, len(amounts), 3)]:
        kb.row(
            *[
                InlineKeyboardButton(
                    text=f"{amount}$",
                    callback_data=f"raffle_amount:{amount}",
                )
                for amount in chunk
            ]
        )

    kb.row(
        InlineKeyboardButton(
            text="⬅️ Назад" if lang == "ru" else "⬅️ Back",
            callback_data="raffle_back",
        )
    )
    return kb.as_markup()


def raffle_control_keyboard(raffle_id: int, lang: str):
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(
            text="🎲 Запустить розыгрыш" if lang == "ru" else "🎲 Draw winner",
            callback_data=f"raffle_finish:{raffle_id}",
        )
    )
    kb.row(
        InlineKeyboardButton(
            text="⬅️ Меню" if lang == "ru" else "⬅️ Menu",
            callback_data="back",
        )
    )
    return kb.as_markup()


def raffle_join_keyboard(raffle_id: int, lang: str):
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(
            text="✅ Участвовать" if lang == "ru" else "✅ Join",
            callback_data=f"raffle_join:{raffle_id}",
        )
    )
    return kb.as_markup()
