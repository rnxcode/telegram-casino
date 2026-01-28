from aiogram.fsm.state import StatesGroup, State

class AdminState(StatesGroup):
    waiting_user_id = State()
    waiting_amount = State()
    waiting_channels = State()
    waiting_requisite_key = State()
    waiting_requisite_value = State()
    waiting_duel_log = State()
