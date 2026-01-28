import random
from services.balance import change_balance, get_balance

DICE_PAYOUTS = {
    "over": 1.9,
    "under": 1.9,
    "even": 1.95,
    "odd": 1.95,
    "num1": 5,
    "num2": 5,
    "num3": 5,
    "num4": 5,
    "num5": 5,
    "num6": 5,
}

async def play_dice(user_id: int, bet_type: str):
    roll = random.randint(1, 6)
    bet = 10  # можно сделать динамическим

    await change_balance(user_id, -bet)

    win = False

    if bet_type == "over": win = roll > 3
    elif bet_type == "under": win = roll < 4
    elif bet_type == "even": win = roll % 2 == 0
    elif bet_type == "odd": win = roll % 2 != 0
    else:  # num1..num6
        target = int(bet_type[-1])
        win = roll == target

    win_amount = int(bet * DICE_PAYOUTS[bet_type]) if win else 0

    if win:
        await change_balance(user_id, win_amount)

    return win, win_amount, roll
