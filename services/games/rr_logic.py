import random

MULT = {
    1: 1.2,
    2: 1.5,
    3: 2.0,
    4: 2.8,
    5: 4.0,
}


def rr_start(bet: int):
    return {"bet": bet, "stage": 1}


def rr_shoot(stage: int) -> bool:
    chambers = 7 - stage  # 6..2
    shot = random.randint(1, chambers)
    return shot == 1


def rr_win(bet: int, stage: int) -> int:

    return int(bet * MULT.get(stage, 1))
