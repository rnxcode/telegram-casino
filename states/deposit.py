# states/deposit.py
from aiogram.fsm.state import StatesGroup, State

class DepositState(StatesGroup):
    waiting_amount = State()
    waiting_rocket_check = State()
