from aiogram.fsm.state import StatesGroup, State

class WithdrawState(StatesGroup):
    waiting_amount = State()
    waiting_wallet = State()
