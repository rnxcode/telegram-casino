from database.db import db

async def save_game_round(user_id, game_type, bet, result, seed, hash_value, proof):
    await db.execute(
        "INSERT INTO games(user_id, game_type, bet, result, seed, hash, proof) "
        "VALUES(?,?,?,?,?,?,?)",
        (user_id, game_type, bet, result, seed, hash_value, proof)
    )
