from aiogram import Router, F
from aiogram.types import CallbackQuery
from database.db import db
import json

router = Router()

@router.callback_query(F.data.startswith("proof_"))
async def show_proof(call: CallbackQuery, lang: str):

    game_id = int(call.data.split("_")[1])

    row = await db.fetchone(
        "SELECT seed, hash, proof FROM games WHERE id=?",
        (game_id,)
    )

    if not row:
        return await call.answer("Not found", show_alert=True)

    seed, hash_value, proof_raw = row
    proof = json.loads(proof_raw)

    text = (
        f"🔐 <b>Проверка честности</b>\n\n"
        f"Seed:\n<code>{seed}</code>\n\n"
        f"Hash (SHA-256):\n<code>{hash_value}</code>\n\n"
        f"Proof:\n<code>{proof}</code>"
        if lang == "ru"
        else
        f"🔐 <b>Fairness Check</b>\n\n"
        f"Seed:\n<code>{seed}</code>\n\n"
        f"Hash (SHA-256):\n<code>{hash_value}</code>\n\n"
        f"Proof:\n<code>{proof}</code>"
    )

    await call.message.edit_text(text)

import random
import hashlib

def generate_round():
    """
    Старый интерфейс, который ожидают твои игры.
    Возвращает:
    - crash (float)
    - seed (str)
    - hash_value (str)
    """

    crash = round(random.uniform(1.0, 5.0), 2)  # классика
    seed = f"{crash}:{random.randint(100000, 999999999)}"
    hash_value = hashlib.sha256(seed.encode()).hexdigest()

    return crash, seed, hash_value


# Новый интерфейс для улучшенной честности
def generate_fair_round(game_type: str):
    """
    Расширенный формат для будущих игр и честности.
    """
    crash, seed, hash_value = generate_round()

    proof = {
        "seed": seed,
        "game_type": game_type,
        "result": crash
    }

    return crash, seed, hash_value, proof
