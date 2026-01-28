from datetime import datetime
from database.db import db
from services.notifications import send_game_log


# -------------------
#     RUSSIAN ROULETTE
# -------------------

async def log_rr_game(user_id, bet, stage, win, result, username=None):
    await db.execute("""
        UPDATE users SET
            games_played = games_played + 1,
            rr_played = rr_played + 1
        WHERE user_id = ?
    """, (user_id,))

    if result in ("win", "take"):
        await db.execute("""
            UPDATE users SET
                games_won = games_won + 1,
                rr_won = rr_won + 1,
                profit_won = profit_won + ?
        WHERE user_id = ?
        """, (win, user_id))

        await send_game_log(
            bot=None,
            text=(
                f"🔫 Russian Roulette WIN\n"
                f"User: {user_id}\n"
                f"Bet: {bet}\n"
                f"Win: {win}\n"
                f"Stage: {stage}"
            ),
        )

    elif result == "lose":
        await db.execute("""
            UPDATE users SET
                games_lost = games_lost + 1,
                rr_lost = rr_lost + 1,
                profit_lost = profit_lost + ?
            WHERE user_id = ?
        """, (bet, user_id))

    await db.execute("""
        INSERT INTO games (user_id, game_type, bet, result, stage)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, "russian", bet, result, stage))


# -------------------
#       BLACKJACK
# -------------------

async def log_bj_game(user_id, bet, win, result, username=None):

    await db.execute("""
        UPDATE users SET
            games_played = games_played + 1,
            bj_played = bj_played + 1
        WHERE user_id = ?
    """, (user_id,))

    if result in ("win", "blackjack"):
        await db.execute("""
            UPDATE users SET
                games_won = games_won + 1,
                bj_won = bj_won + 1,
                profit_won = profit_won + ?
            WHERE user_id = ?
        """, (win, user_id))

        await send_game_log(
            bot=None,
            text=(
                f"🃏 Blackjack WIN\n"
                f"User: {user_id}\n"
                f"Bet: {bet}\n"
                f"Win: {win}"
            ),
        )

    elif result == "lose":
        await db.execute("""
            UPDATE users SET
                games_lost = games_lost + 1,
                bj_lost = bj_lost + 1,
                profit_lost = profit_lost + ?
            WHERE user_id = ?
        """, (bet, user_id))

    await db.execute("""
        INSERT INTO games (user_id, game_type, bet, result)
        VALUES (?, ?, ?, ?)
    """, (user_id, "blackjack", bet, result))


# -------------------
#        MINES
# -------------------

async def log_mines_game(user_id, bet, win, result, username=None, mines_count=None):
    await db.execute("""
        UPDATE users SET
            games_played = games_played + 1,
            mines_played = mines_played + 1
        WHERE user_id = ?
    """, (user_id,))

    if result in ("win", "cashout"):
        await db.execute("""
            UPDATE users SET
                games_won = games_won + 1,
                mines_won = mines_won + 1,
                profit_won = profit_won + ?
            WHERE user_id = ?
        """, (win, user_id))

        extra = f"\nMines: {mines_count}" if mines_count else ""
        await send_game_log(
            bot=None,
            text=(
                f"💣 Mines WIN\n"
                f"User: {user_id}\n"
                f"Bet: {bet}\n"
                f"Win: {win}{extra}"
            ),
        )

    elif result == "lose":
        await db.execute("""
            UPDATE users SET
                games_lost = games_lost + 1,
                mines_lost = mines_lost + 1,
                profit_lost = profit_lost + ?
            WHERE user_id = ?
        """, (bet, user_id))

    await db.execute("""
        INSERT INTO games (user_id, game_type, bet, result)
        VALUES (?, ?, ?, ?)
    """, (user_id, "mines", bet, result))


# -------------------
#        DICE
# -------------------

async def log_dice_game(user_id, bet, win, result, username=None, multiplier=None):

    await db.execute("""
        UPDATE users SET
            games_played = games_played + 1,
            dice_played = dice_played + 1
        WHERE user_id = ?
    """, (user_id,))

    if result == "win":
        await db.execute("""
            UPDATE users SET
                games_won = games_won + 1,
                dice_won = dice_won + 1,
                profit_won = profit_won + ?
        WHERE user_id = ?
        """, (win, user_id))

        extra = f"\nMultiplier: {multiplier}" if multiplier else ""
        await send_game_log(
            bot=None,
            text=(
                f"🎲 Dice WIN\n"
                f"User: {user_id}\n"
                f"Bet: {bet}\n"
                f"Win: {win}{extra}"
            ),
        )

    elif result == "lose":
        await db.execute("""
            UPDATE users SET
                games_lost = games_lost + 1,
                dice_lost = dice_lost + 1,
                profit_lost = profit_lost + ?
            WHERE user_id = ?
        """, (bet, user_id))

    await db.execute("""
        INSERT INTO games (user_id, game_type, bet, result)
        VALUES (?, ?, ?, ?)
    """, (user_id, "dice", bet, result))


# -------------------
#        ROULETTE
# -------------------

async def log_roulette_game(user_id, bet, win, result, username=None):
    await db.execute("""
        UPDATE users SET
            games_played = games_played + 1,
            roulette_played = roulette_played + 1
        WHERE user_id = ?
    """, (user_id,))

    if result == "win":
        await db.execute("""
            UPDATE users SET
                games_won = games_won + 1,
                roulette_won = roulette_won + 1,
                profit_won = profit_won + ?
        WHERE user_id = ?
        """, (win, user_id))

        await send_game_log(
            bot=None,
            text=(
                f"🎰 Roulette WIN\n"
                f"User: {user_id}\n"
                f"Bet: {bet}\n"
                f"Win: {win}"
            ),
        )

    elif result == "lose":
        await db.execute("""
            UPDATE users SET
                games_lost = games_lost + 1,
                roulette_lost = roulette_lost + 1,
                profit_lost = profit_lost + ?
            WHERE user_id = ?
        """, (bet, user_id))

    await db.execute("""
        INSERT INTO games (user_id, game_type, bet, result)
        VALUES (?, ?, ?, ?)
    """, (user_id, "roulette", bet, result))


async def close_bot():
    return
