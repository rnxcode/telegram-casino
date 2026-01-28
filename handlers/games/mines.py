# handlers/games/mines.py
import asyncio
import random
from typing import List, Dict, Tuple
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.menu import main_menu
from services.balance import get_balance, change_balance
from services.game_stats import log_mines_game
from database.db import db

router = Router()


# ================================
#  FSM
# ================================
class MinesState(StatesGroup):
    waiting_bet = State()
    waiting_mines = State()
    playing = State()


# ================================
#  GAME CLASS
# ================================
class MinesGame:
    def __init__(self, bet: float, mines_count: int = 3):
        self.bet = bet
        self.mines_count = min(max(mines_count, 1), 24)
        self.board_size = 25
        self.mines: List[int] = []
        self.opened_cells: List[int] = []
        self.game_over = False
        self.won = False
        self.current_multiplier = 1.0

        self.generate_mines()
        self.multipliers = self.calculate_multipliers()

    def generate_mines(self):
        all_cells = list(range(self.board_size))
        self.mines = random.sample(all_cells, self.mines_count)

    def calculate_multipliers(self) -> Dict[int, float]:
        multipliers = {}
        safe_cells = self.board_size - self.mines_count

        for opened in range(1, safe_cells + 1):
            probability = (safe_cells - opened) / safe_cells
            if probability > 0:
                multiplier = round(0.96 / probability, 2)
                multipliers[opened] = multiplier

        return multipliers

    def open_cell(self, cell_index: int) -> Tuple[bool, float]:
        if cell_index in self.opened_cells:
            return False, self.current_multiplier

        self.opened_cells.append(cell_index)

        if cell_index in self.mines:
            self.game_over = True
            self.won = False
            return True, 0.0

        opened_count = len(self.opened_cells)
        if opened_count in self.multipliers:
            self.current_multiplier = self.multipliers[opened_count]

        if opened_count == self.board_size - self.mines_count:
            self.game_over = True
            self.won = True

        return False, self.current_multiplier

    def cashout(self):
        if not self.game_over and len(self.opened_cells) > 0:
            self.game_over = True
            self.won = True
            return True
        return False

    def get_win_amount(self) -> float:
        return round(self.bet * self.current_multiplier, 2) if self.won else 0.0

    def get_board_display(self, reveal_mines: bool = False) -> List[List[str]]:
        board = []
        for i in range(self.board_size):
            row = i // 5
            col = i % 5

            if i in self.opened_cells:
                if i in self.mines:
                    symbol = "💥"
                else:
                    mines_around = self.count_mines_around(i)
                    symbol = f"{mines_around}" if mines_around > 0 else "🟩"
            elif self.game_over and reveal_mines and i in self.mines:
                symbol = "💣"
            else:
                symbol = "⬜"

            if len(board) <= row:
                board.append([])
            board[row].append(symbol)

        return board

    def count_mines_around(self, cell_index: int) -> int:
        count = 0
        row = cell_index // 5
        col = cell_index % 5

        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue

                nr, nc = row + dr, col + dc
                if 0 <= nr < 5 and 0 <= nc < 5:
                    neigh = nr * 5 + nc
                    if neigh in self.mines:
                        count += 1

        return count


# ================================
#  TEXTS — чистый современный UI
# ================================
def mines_game_text(lang: str, game: MinesGame, balance: float) -> str:
    opened = len(game.opened_cells)
    max_safe = 25 - game.mines_count

    if lang == "ru":
        return (
            f"<b>🎯 Мины</b>\n\n"
            f"💵 Ставка: <b>{game.bet:.2f}$</b>\n"
            f"💰 Баланс: <b>{balance:.2f}$</b>\n"
            f"💣 Мин: <b>{game.mines_count}</b>\n\n"
            f"🟩 Открыто: <b>{opened}/{max_safe}</b>\n"
            f"📈 Множитель: <b>{game.current_multiplier:.2f}x</b>\n"
            f"🏆 Потенциал: <b>{game.bet * game.current_multiplier:.2f}$</b>\n\n"
            f"Выберите клетку:"
        )
    else:
        return (
            f"<b>🎯 Mines</b>\n\n"
            f"💵 Bet: <b>{game.bet:.2f}$</b>\n"
            f"💰 Balance: <b>{balance:.2f}$</b>\n"
            f"💣 Mines: <b>{game.mines_count}</b>\n\n"
            f"🟩 Opened: <b>{opened}/{max_safe}</b>\n"
            f"📈 Multiplier: <b>{game.current_multiplier:.2f}x</b>\n"
            f"🏆 Potential: <b>{game.bet * game.current_multiplier:.2f}$</b>\n\n"
            f"Choose a cell:"
        )


def mines_result_text(lang: str, game: MinesGame, win_amount: float) -> str:
    opened = len(game.opened_cells)

    if game.won:
        if lang == "ru":
            return (
                f"<b>🎉 Победа!</b>\n\n"
                f"🏆 Вы выиграли: <b>{win_amount:.2f}$</b>\n"
                f"📈 Множитель: <b>{game.current_multiplier:.2f}x</b>\n"
                f"📦 Открыто клеток: <b>{opened}</b>"
            )
        else:
            return (
                f"<b>🎉 Victory!</b>\n\n"
                f"🏆 Win: <b>{win_amount:.2f}$</b>\n"
                f"📈 Multiplier: <b>{game.current_multiplier:.2f}x</b>\n"
                f"📦 Cells opened: <b>{opened}</b>"
            )
    else:
        if lang == "ru":
            return (
                f"<b>💥 Проигрыш</b>\n\n"
                f"💸 Потеряно: <b>{game.bet:.2f}$</b>\n"
                f"📦 Открыто клеток: <b>{opened}</b>"
            )
        else:
            return (
                f"<b>💥 Lost</b>\n\n"
                f"💸 Lost: <b>{game.bet:.2f}$</b>\n"
                f"📦 Cells opened: <b>{opened}</b>"
            )


# ================================
# ВЫИГРЫШНАЯ АНИМАЦИЯ
# ================================
async def animate_win(message, lang: str, game: MinesGame, final_amount: float):
    steps = 6
    for i in range(1, steps + 1):
        amount = final_amount * (i / steps)
        if lang == "ru":
            text = (
                f"<b>🎉 Победа!</b>\n\n"
                f"🏆 Вы выиграли: <b>{amount:.2f}$</b>\n"
                f"📈 Множитель: <b>{game.current_multiplier:.2f}x</b>"
            )
        else:
            text = (
                f"<b>🎉 Victory!</b>\n\n"
                f"🏆 Win: <b>{amount:.2f}$</b>\n"
                f"📈 Multiplier: <b>{game.current_multiplier:.2f}x</b>"
            )

        await message.edit_text(text)
        await asyncio.sleep(0.18)


# ================================
#  KEYBOARDS
# ================================
def mines_board_keyboard(game: MinesGame, lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    display = game.get_board_display(reveal_mines=game.game_over)

    for r in range(5):
        for c in range(5):
            idx = r * 5 + c
            symbol = display[r][c]

            if game.game_over or idx in game.opened_cells:
                cb = "mines_noop"
            else:
                cb = f"mines_cell_{idx}"

            builder.add(InlineKeyboardButton(text=symbol, callback_data=cb))

    builder.adjust(5)

    if game.game_over:
        if lang == "ru":
            builder.row(
                InlineKeyboardButton(text="🔄 Новая игра", callback_data="mines_new_game"),
                InlineKeyboardButton(text="⬅️ Меню", callback_data="mines_exit")
            )
        else:
            builder.row(
                InlineKeyboardButton(text="🔄 New Game", callback_data="mines_new_game"),
                InlineKeyboardButton(text="⬅️ Menu", callback_data="mines_exit")
            )
    else:
        if lang == "ru":
            builder.row(
                InlineKeyboardButton(text="💰 Забрать", callback_data="mines_cashout"),
                InlineKeyboardButton(text="⬅️ Меню", callback_data="mines_exit")
            )
        else:
            builder.row(
                InlineKeyboardButton(text="💰 Cashout", callback_data="mines_cashout"),
                InlineKeyboardButton(text="⬅️ Menu", callback_data="mines_exit")
            )

    return builder.as_markup()


# ================================
#  ХЕНДЛЕРЫ
# ================================

@router.callback_query(F.data == "game_mines")
async def mines_start(call: CallbackQuery, state: FSMContext, lang: str):
    balance = await get_balance(call.from_user.id)

    await state.set_state(MinesState.waiting_bet)

    text = (
        f"<b>💵 Выбор ставки</b>\n\nБаланс: <b>{balance:.2f}$</b>\n\nВведите сумму или выберите кнопку."
        if lang == "ru" else
        f"<b>💵 Choose Bet</b>\n\nBalance: <b>{balance:.2f}$</b>\n\nEnter custom amount or choose below."
    )

    kb = InlineKeyboardBuilder()
    for row in [(1,5,10),(30,50,100)]:
        kb.row(*[InlineKeyboardButton(text=f"{v}$", callback_data=f"mines_bet_{v}") for v in row])
    kb.row(InlineKeyboardButton(text="⬅️ Назад" if lang=="ru" else "⬅️ Back", callback_data="games_menu"))

    await call.message.edit_text(text, reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("mines_bet_"), MinesState.waiting_bet)
async def mines_set_bet(call: CallbackQuery, state: FSMContext, lang: str):
    bet = float(call.data.split("_")[2])
    balance = await get_balance(call.from_user.id)
    if balance < bet:
        await call.answer(
            "Недостаточно средств. Пополните или выберите меньшую ставку."
            if lang == "ru"
            else "Not enough balance. Top up or choose a smaller bet.",
            show_alert=True,
        )
        return await mines_start(call, state, lang)

    await state.update_data(bet=bet)
    await state.set_state(MinesState.waiting_mines)

    text = (
        f"<b>💣 Количество мин</b>\n\nСтавка: <b>{bet:.2f}$</b>\nВыберите количество мин:"
        if lang == "ru" else
        f"<b>💣 Number of mines</b>\n\nBet: <b>{bet:.2f}$</b>\nChoose number of mines:"
    )

    kb = InlineKeyboardBuilder()
    for row in [(8,10),(15,20,24)]:
        kb.row(*[InlineKeyboardButton(text=str(v), callback_data=f"mines_count_{v}") for v in row])
    kb.row(InlineKeyboardButton(text="⬅️ Назад" if lang=="ru" else "⬅️ Back", callback_data="game_mines"))

    await call.message.edit_text(text, reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("mines_count_"), MinesState.waiting_mines)
async def mines_set_count(call: CallbackQuery, state: FSMContext, lang: str):
    user_id = call.from_user.id
    mines_count = int(call.data.split("_")[2])

    d = await state.get_data()
    bet = d["bet"]

    await change_balance(user_id, -bet)

    game = MinesGame(bet, mines_count)

    await state.update_data(game={
        "bet": game.bet,
        "mines": game.mines,
        "mines_count": game.mines_count,
        "opened_cells": [],
        "game_over": False,
        "won": False,
        "current_multiplier": game.current_multiplier,
        "multipliers": game.multipliers
    })

    await state.set_state(MinesState.playing)

    balance = await get_balance(user_id)
    await call.message.edit_text(mines_game_text(lang, game, balance), reply_markup=mines_board_keyboard(game, lang))


@router.callback_query(F.data.startswith("mines_cell_"), MinesState.playing)
async def mines_open_cell(call: CallbackQuery, state: FSMContext, lang: str):
    user_id = call.from_user.id
    idx = int(call.data.split("_")[2])

    data = await state.get_data()
    g = data["game"]

    game = MinesGame(g["bet"], g["mines_count"])
    game.mines = g["mines"]
    game.opened_cells = g["opened_cells"]
    game.game_over = g["game_over"]
    game.won = g["won"]
    game.current_multiplier = g["current_multiplier"]
    game.multipliers = g["multipliers"]

    if game.game_over:
        return await call.answer("Игра окончена" if lang=="ru" else "Finished")

    hit, _ = game.open_cell(idx)

    await state.update_data(game={
        "bet": game.bet,
        "mines": game.mines,
        "mines_count": game.mines_count,
        "opened_cells": game.opened_cells,
        "game_over": game.game_over,
        "won": game.won,
        "current_multiplier": game.current_multiplier,
        "multipliers": game.multipliers
    })

    balance = await get_balance(user_id)

    if hit:
        await log_mines_game(user_id, game.bet, 0, "lose")

        await call.message.edit_text(mines_result_text(lang, game, 0),
                                     reply_markup=mines_board_keyboard(game, lang))
        await asyncio.sleep(4)
        return await state.clear()

    if game.game_over and game.won:
        win = game.get_win_amount()
        await change_balance(user_id, win)
        await log_mines_game(user_id, game.bet, win, "win")

        # Анимация выигрыша
        await animate_win(call.message, lang, game, win)

        await call.message.edit_text(mines_result_text(lang, game, win),
                                     reply_markup=mines_board_keyboard(game, lang))
        await asyncio.sleep(4)
        return await state.clear()

    # игра продолжается
    await call.message.edit_text(mines_game_text(lang, game, balance),
                                 reply_markup=mines_board_keyboard(game, lang))


@router.callback_query(F.data == "mines_cashout", MinesState.playing)
async def mines_cashout(call: CallbackQuery, state: FSMContext, lang: str):
    data = await state.get_data()
    g = data["game"]

    game = MinesGame(g["bet"], g["mines_count"])
    game.mines = g["mines"]
    game.opened_cells = g["opened_cells"]
    game.current_multiplier = g["current_multiplier"]
    game.multipliers = g["multipliers"]
    game.game_over = g["game_over"]

    if game.cashout():
        win = game.get_win_amount()
        await change_balance(call.from_user.id, win)
        await log_mines_game(call.from_user.id, game.bet, win, "cashout")

        await animate_win(call.message, lang, game, win)

        await call.message.edit_text(mines_result_text(lang, game, win),
                                     reply_markup=mines_board_keyboard(game, lang))

        await asyncio.sleep(4)
        await state.clear()
    else:
        await call.answer("Нечего забирать" if lang=="ru" else "Nothing to cashout")


@router.callback_query(F.data == "mines_new_game")
async def mines_new_game(call: CallbackQuery, state: FSMContext, lang: str):
    await state.clear()
    await mines_start(call, state, lang)


@router.callback_query(F.data == "mines_exit")
async def mines_exit(call: CallbackQuery, state: FSMContext, lang: str):
    await state.clear()
    from handlers.menu_games import open_games_menu
    await open_games_menu(call, lang)


@router.callback_query(F.data == "mines_noop")
async def mines_noop(call: CallbackQuery):
    await call.answer()
