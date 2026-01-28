from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def tower_keyboard(seed: str, level: int = 1, opened: list[int] = None) -> InlineKeyboardMarkup:
    """
    Клавиатура для игры Tower.

    level — какой уровень сейчас открыт игроку (1–8)
    opened — список безопасных клеток на пройденных уровнях
    seed — ID раунда, отправляется в callback
    """

    opened = opened or []
    builder = InlineKeyboardBuilder()

    # Tower имеет 8 уровней, в каждом 3 клетки
    TOTAL_LEVELS = 8
    CELLS_PER_LEVEL = 3

    for lvl in range(1, TOTAL_LEVELS + 1):
        row = []

        # закрытые уровни (ещё не достигнуты)
        if lvl > level:
            row = [
                InlineKeyboardButton(text="⬛", callback_data="tower_locked")
                for _ in range(CELLS_PER_LEVEL)
            ]

        # уже пройденные уровни
        elif lvl < level:
            safe = opened[lvl - 1]  # индекс выбранной клетки
            for i in range(CELLS_PER_LEVEL):
                cell = "🟩" if i == safe else "⬛"
                row.append(
                    InlineKeyboardButton(text=cell, callback_data="tower_passed")
                )

        # текущий уровень
        else:
            for i in range(CELLS_PER_LEVEL):
                row.append(
                    InlineKeyboardButton(
                        text="🟦",
                        callback_data=f"tower_step:{seed}:{lvl}:{i}"
                    )
                )

        builder.row(*row)

    # Кнопка забрать выигрыш
    builder.row(
        InlineKeyboardButton(text="💰 Забрать" if True else "💰 Take", callback_data="tower_cashout")
    )

    return builder.as_markup()
