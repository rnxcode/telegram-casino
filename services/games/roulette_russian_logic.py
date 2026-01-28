import random
from services.balance import change_balance, get_balance

STAGE_MULT = {
    1: 1.2,
    2: 1.5,
    3: 2.0,
    4: 2.5,
    5: 3.5,
}

async def rr_start_game(user_id: int, bet: int):
    await change_balance(user_id, -bet)
    return {"bet": bet, "stage": 1}

async def rr_shoot(game_state: dict):
    stage = game_state["stage"]
    chambers = 7 - stage  # на 1 уровне 6:1, на 2 — 5:1 ...

    shot = random.randint(1, chambers)
    is_dead = shot == 1

    return is_dead

async def rr_win_amount(game_state: dict):
    bet = game_state["bet"]
    stage = game_state["stage"]

    if stage in STAGE_MULT:
        return int(bet * STAGE_MULT[stage])
    return 0
