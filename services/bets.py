from database.db import db

async def get_bet(user_id: int):
    row = await db.fetchone(
        "SELECT amount, balance_type FROM bets WHERE user_id=?",
        (user_id,)
    )
    if row:
        return row[0], row[1]
    return 1, "balance"


async def set_bet(user_id: int, amount: float):
    exists = await db.fetchone(
        "SELECT user_id FROM bets WHERE user_id=?",
        (user_id,)
    )

    if exists:
        await db.execute(
            "UPDATE bets SET amount=? WHERE user_id=?",
            (amount, user_id)
        )
    else:
        await db.execute(
            "INSERT INTO bets(user_id, amount) VALUES(?, ?)",
            (user_id, amount)
        )


async def set_balance_type(user_id: int, balance_type: str):
    await db.execute(
        "UPDATE bets SET balance_type=? WHERE user_id=?",
        (balance_type, user_id)
    )
