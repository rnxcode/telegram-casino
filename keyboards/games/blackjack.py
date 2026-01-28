# keyboards/games/blackjack.py
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def bj_keyboard(lang: str, game=None, first_move: bool = False, game_over: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура для игры в блэкджек"""
    builder = InlineKeyboardBuilder()

    if game_over:
        # После окончания игры
        if lang == "ru":
            builder.row(
                InlineKeyboardButton(text="🔄 Новая игра", callback_data="bj_new_game"),
                InlineKeyboardButton(text="⬅️ Выход", callback_data="bj_exit")
            )
        else:
            builder.row(
                InlineKeyboardButton(text="🔄 New Game", callback_data="bj_new_game"),
                InlineKeyboardButton(text="⬅️ Exit", callback_data="bj_exit")
            )
    elif game and not game.game_over:
        # Во время игры
        player_value, _ = game.calculate_hand_value(game.player_hand)

        if lang == "ru":
            builder.row(
                InlineKeyboardButton(text="🎴 Ещё", callback_data="bj_hit"),
                InlineKeyboardButton(text="✋ Хватит", callback_data="bj_stand")
            )

            # Удвоение доступно только на первом ходу
            if first_move and len(game.player_hand) == 2 and player_value in [9, 10, 11]:
                builder.row(
                    InlineKeyboardButton(text="💰 Удвоить", callback_data="bj_double")
                )
        else:
            builder.row(
                InlineKeyboardButton(text="🎴 Hit", callback_data="bj_hit"),
                InlineKeyboardButton(text="✋ Stand", callback_data="bj_stand")
            )

            if first_move and len(game.player_hand) == 2 and player_value in [9, 10, 11]:
                builder.row(
                    InlineKeyboardButton(text="💰 Double", callback_data="bj_double")
                )

    # Кнопка выхода всегда доступна
    if lang == "ru":
        builder.row(InlineKeyboardButton(text="🚪 Выйти", callback_data="bj_exit"))
    else:
        builder.row(InlineKeyboardButton(text="🚪 Exit", callback_data="bj_exit"))

    return builder.as_markup()


def bj_bet_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Клавиатура для выбора ставки"""
    builder = InlineKeyboardBuilder()

    if lang == "ru":
        builder.row(
            InlineKeyboardButton(text="1 $", callback_data="bj_bet_1"),
            InlineKeyboardButton(text="5 $", callback_data="bj_bet_5"),
            InlineKeyboardButton(text="10 $", callback_data="bj_bet_10")
        )
        builder.row(
            InlineKeyboardButton(text="30 $", callback_data="bj_bet_30"),
            InlineKeyboardButton(text="50 $", callback_data="bj_bet_50"),
            InlineKeyboardButton(text="100 $", callback_data="bj_bet_100")
        )
        builder.row(
            InlineKeyboardButton(text="⬅️ Назад", callback_data="games_menu")
        )
    else:
        builder.row(
            InlineKeyboardButton(text="1 $", callback_data="bj_bet_1"),
            InlineKeyboardButton(text="5 $", callback_data="bj_bet_5"),
            InlineKeyboardButton(text="10 $", callback_data="bj_bet_10")
        )
        builder.row(
            InlineKeyboardButton(text="30 $", callback_data="bj_bet_30"),
            InlineKeyboardButton(text="50 $", callback_data="bj_bet_50"),
            InlineKeyboardButton(text="100 $", callback_data="bj_bet_100")
        )
        builder.row(
            InlineKeyboardButton(text="⬅️ Back", callback_data="games_menu")
        )

    return builder.as_markup()
