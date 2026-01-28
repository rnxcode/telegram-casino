# handlers/games/blackjack.py
import asyncio
import random
from typing import List, Tuple, Dict, Any
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from keyboards.menu import main_menu
from keyboards.games.blackjack import bj_bet_keyboard, bj_keyboard
from services.balance import get_balance, change_balance
from services.game_stats import log_bj_game

router = Router()


# --------------------------------------
# SAFE EDIT to avoid "message is not modified"
# --------------------------------------
async def safe_edit(message, text: str, reply_markup=None):
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except Exception as e:
        if "message is not modified" in str(e).lower():
            return
        raise


# --------------------------------------
# FSM
# --------------------------------------
class BlackjackState(StatesGroup):
    waiting_bet = State()
    game_active = State()


# --------------------------------------
# CARD ENGINE
# --------------------------------------
SUITS = ["spades", "hearts", "diamonds", "clubs"]
SUIT_EMOJI = {"spades": "♠️", "hearts": "♥️", "diamonds": "♦️", "clubs": "♣️"}
RANKS = ['2','3','4','5','6','7','8','9','10','J','Q','K','A']


class Card:
    def __init__(self, rank: str, suit: str):
        self.rank = rank
        self.suit = suit

    @property
    def value(self) -> int:
        if self.rank in ['J','Q','K']:
            return 10
        if self.rank == 'A':
            return 11
        return int(self.rank)

    def __str__(self):
        return f"{self.rank}{SUIT_EMOJI[self.suit]}"

    def to_tuple(self):
        return (self.rank, self.suit)

    @staticmethod
    def from_tuple(t):
        return Card(t[0], t[1])


class Deck:
    def __init__(self, num_decks: int = 6, cards=None):
        if cards:
            self.cards = [Card.from_tuple(t) for t in cards]
        else:
            self.cards = []
            for _ in range(num_decks):
                for s in SUITS:
                    for r in RANKS:
                        self.cards.append(Card(r, s))
            random.shuffle(self.cards)

    def draw(self):
        if not self.cards:
            self.__init__()  # reset
        return self.cards.pop()

    def serialize(self):
        return [c.to_tuple() for c in self.cards]


# --------------------------------------
# GAME LOGIC
# --------------------------------------
class BlackjackGame:
    def __init__(self, bet, deck=None):
        self.bet = bet
        self.deck = deck or Deck()

        self.player_hand = []
        self.dealer_hand = []
        self.game_over = False
        self.result = ""

        self.player_hand.append(self.deck.draw())
        self.dealer_hand.append(self.deck.draw())
        self.player_hand.append(self.deck.draw())
        self.dealer_hand.append(self.deck.draw())

    def calculate_hand_value(self, hand):
        total = 0
        aces = 0
        for c in hand:
            if c.rank == "A":
                total += 11
                aces += 1
            elif c.rank in ["J", "Q", "K"]:
                total += 10
            else:
                total += int(c.rank)
        while total > 21 and aces:
            total -= 10
            aces -= 1
        soft = any(c.rank == "A" for c in hand) and total <= 21
        return total, soft

    def hit(self):
        self.player_hand.append(self.deck.draw())
        v, _ = self.calculate_hand_value(self.player_hand)
        if v > 21:
            self.result = "bust"
            self.game_over = True

    def dealer_turn(self):
        v, _ = self.calculate_hand_value(self.dealer_hand)
        while v < 17:
            self.dealer_hand.append(self.deck.draw())
            v, _ = self.calculate_hand_value(self.dealer_hand)

    def stand(self):
        self.dealer_turn()
        self.determine_winner()

    def can_double(self):
        return len(self.player_hand) == 2

    def double(self):
        self.bet *= 2
        self.player_hand.append(self.deck.draw())
        v, _ = self.calculate_hand_value(self.player_hand)
        if v > 21:
            self.result = "bust"
            self.game_over = True
        else:
            self.stand()

    def determine_winner(self):
        pv, _ = self.calculate_hand_value(self.player_hand)
        dv, _ = self.calculate_hand_value(self.dealer_hand)
        self.game_over = True

        if pv > 21:
            self.result = "bust"
        elif dv > 21:
            self.result = "dealer_bust"
        elif pv == dv:
            self.result = "push"
        elif pv == 21 and len(self.player_hand) == 2:
            self.result = "blackjack"
        elif pv > dv:
            self.result = "win"
        else:
            self.result = "lose"

    def get_payout(self):
        if self.result == "blackjack":
            return self.bet * 2.5
        if self.result in ("win", "dealer_bust"):
            return self.bet * 2
        if self.result == "push":
            return self.bet
        return 0

    def format_hand(self, hand, hide_first=False):
        if hide_first:
            return "❓ " + " ".join(str(c) for c in hand[1:])
        return " ".join(str(c) for c in hand)

    def serialize(self):
        return {
            "bet": self.bet,
            "deck": self.deck.serialize(),
            "player_hand": [c.to_tuple() for c in self.player_hand],
            "dealer_hand": [c.to_tuple() for c in self.dealer_hand],
            "game_over": self.game_over,
            "result": self.result
        }

    @staticmethod
    def deserialize(data):
        deck = Deck(cards=data["deck"])
        g = BlackjackGame(data["bet"], deck)
        g.player_hand = [Card.from_tuple(t) for t in data["player_hand"]]
        g.dealer_hand = [Card.from_tuple(t) for t in data["dealer_hand"]]
        g.game_over = data["game_over"]
        g.result = data["result"]
        return g


# --------------------------------------
# TEXTS
# --------------------------------------
def bj_display(lang, game, balance_after_bet, hide_dealer=True):
    pv, soft = game.calculate_hand_value(game.player_hand)
    dealer_line = game.format_hand(game.dealer_hand, hide_first=hide_dealer)

    if lang == "ru":
        return (
            f"🃏 <b>Блэкджек</b>\n\n"
            f"💵 Ставка: <b>{game.bet:.2f}$</b>\n"
            f"💰 Баланс: <b>{balance_after_bet:.2f}$</b>\n\n"
            f"🎯 Ваши карты: {game.format_hand(game.player_hand)}\n"
            f"💎 Сумма: {pv}\n\n"
            f"🤵 Карты дилера: {dealer_line}\n"
        )
    else:
        return (
            f"🃏 <b>Blackjack</b>\n\n"
            f"💵 Bet: <b>{game.bet:.2f}$</b>\n"
            f"💰 Balance: <b>{balance_after_bet:.2f}$</b>\n\n"
            f"🎯 Your cards: {game.format_hand(game.player_hand)}\n"
            f"💎 Total: {pv}\n\n"
            f"🤵 Dealer: {dealer_line}\n"
        )


def bj_result_text(lang, game, payout):
    pv, _ = game.calculate_hand_value(game.player_hand)
    dv, _ = game.calculate_hand_value(game.dealer_hand)

    if lang == "ru":
        return (
            f"🎲 <b>Результат</b>\n\n"
            f"Ваши карты ({pv}): {game.format_hand(game.player_hand)}\n"
            f"Карты дилера ({dv}): {game.format_hand(game.dealer_hand)}\n\n"
            f"💵 Выплата: {payout:.2f}$"
        )
    else:
        return (
            f"🎲 <b>Result</b>\n\n"
            f"Your cards ({pv}): {game.format_hand(game.player_hand)}\n"
            f"Dealer cards ({dv}): {game.format_hand(game.dealer_hand)}\n\n"
            f"💵 Payout: {payout:.2f}$"
        )


# --------------------------------------
# START
# --------------------------------------
@router.callback_query(F.data == "game_blackjack")
async def bj_start(call: CallbackQuery, state: FSMContext, lang: str):
    await state.set_state(BlackjackState.waiting_bet)

    await safe_edit(
        call.message,
        "Выберите ставку:" if lang == "ru" else "Choose bet:",
        reply_markup=bj_bet_keyboard(lang)
    )


# --------------------------------------
# SET BET
# --------------------------------------
@router.callback_query(F.data.startswith("bj_bet_"), BlackjackState.waiting_bet)
async def bj_set_bet(call: CallbackQuery, state: FSMContext, lang: str):
    bet = float(call.data.split("_")[2])
    user_id = call.from_user.id

    balance = await get_balance(user_id)
    if balance < bet:
        await call.answer(
            "Недостаточно средств. Пополните или выберите меньшую ставку."
            if lang == "ru"
            else "Not enough funds. Top up or pick a smaller bet.",
            show_alert=True,
        )
        return await safe_edit(
            call.message,
            "Выберите ставку:" if lang == "ru" else "Choose bet:",
            reply_markup=bj_bet_keyboard(lang),
        )

    await change_balance(user_id, -bet)

    game = BlackjackGame(bet)
    await state.update_data(game_data=game.serialize())
    await state.set_state(BlackjackState.game_active)

    await safe_edit(call.message, "🔀 Перемешиваем..." if lang == "ru" else "🔀 Shuffling...")
    await asyncio.sleep(0.4)

    await safe_edit(
        call.message,
        bj_display(lang, game, balance - bet, hide_dealer=True),
        reply_markup=bj_keyboard(lang, game, first_move=True)
    )


# --------------------------------------
# MAIN ACTION HANDLER
# --------------------------------------
@router.callback_query(F.data.startswith("bj_"), BlackjackState.game_active)
async def bj_action(call: CallbackQuery, state: FSMContext, lang: str):
    user_id = call.from_user.id
    action = call.data.split("_", 1)[1]

    data = await state.get_data()
    game = BlackjackGame.deserialize(data["game_data"])
    balance = await get_balance(user_id)

    # ---- ACTIONS ----
    if action == "hit":
        await safe_edit(
            call.message,
            bj_display(lang, game, balance - game.bet, hide_dealer=True) + "\n\n⏳...",
        )
        await asyncio.sleep(0.35)
        game.hit()

    elif action == "stand":
        await safe_edit(
            call.message,
            bj_display(lang, game, balance - game.bet, hide_dealer=True)
            + ("\n\n🤵 Дилер думает..." if lang == "ru" else "\n\n🤵 Dealer thinking...")
        )
        await asyncio.sleep(0.5)
        game.stand()

    elif action == "double":
        if not game.can_double():
            return await call.answer(
                "Можно удвоить только с двумя картами" if lang == "ru" else "Only possible on two cards",
                show_alert=True
            )
        if balance < game.bet:
            return await call.answer(
                "Недостаточно средств" if lang == "ru" else "Not enough funds",
                show_alert=True
            )

        await change_balance(user_id, -game.bet)

        await safe_edit(
            call.message,
            bj_display(lang, game, balance - game.bet, hide_dealer=True)
            + ("\n\n💨 Удваиваем..." if lang == "ru" else "\n\n💨 Doubling...")
        )
        await asyncio.sleep(0.45)
        game.double()

    elif action == "exit":
        await state.clear()
        from handlers.menu_games import open_games_menu
        return await open_games_menu(call, lang)

    # SAVE STATE
    await state.update_data(game_data=game.serialize())

    # ---- GAME OVER ----
    if game.game_over:
        # Reveal
        for _ in range(2):
            await asyncio.sleep(0.45)
            await safe_edit(
                call.message,
                bj_display(lang, game, balance - game.bet, hide_dealer=False)
            )

        payout = game.get_payout()
        if payout > 0:
            await change_balance(user_id, payout)

        result_type = "win" if payout > game.bet else ("push" if payout == game.bet else "lose")
        await log_bj_game(user_id, game.bet, payout, result_type)

        # **NEW DEAL button added**
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        kb = InlineKeyboardBuilder()
        kb.button(text="🆕 Новая раздача" if lang == "ru" else "🆕 New deal", callback_data="game_blackjack")
        kb.button(text="⬅️ Назад" if lang == "ru" else "⬅️ Back", callback_data="bj_exit")
        kb.adjust(1)

        await safe_edit(
            call.message,
            bj_result_text(lang, game, payout),
            reply_markup=kb.as_markup()
        )

        await state.clear()
        return

    # ---- CONTINUE GAME ----
    await safe_edit(
        call.message,
        bj_display(lang, game, balance - game.bet, hide_dealer=True),
        reply_markup=bj_keyboard(lang, game)
    )


# --------------------------------------
# EXIT HANDLER
# --------------------------------------
@router.callback_query(F.data == "bj_exit")
async def bj_exit(call: CallbackQuery, state: FSMContext, lang: str):
    await state.clear()
    from handlers.menu_games import open_games_menu
    await open_games_menu(call, lang)
