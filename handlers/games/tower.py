from aiogram import Router, F
from aiogram.types import CallbackQuery
from asyncio import sleep

from services.fairness import generate_fair_round
from keyboards.games import tower_keyboard
from services.bets import get_bet

router = Router()


@router.callback_query(F.data == "game_tower")
async def tower_start(call: CallbackQuery, lang: str):
    user_id = call.from_user.id

    bet, balance_type = await get_bet(user_id)

    # fair round → tower
    tower_map, seed, hash_value, proof = generate_fair_round("tower")

    # -----------------------------
    # ЛОКАЛИЗАЦИЯ
    # -----------------------------
    if lang == "ru":
        title = "🧱 <b>Башня</b>"
        bet_line = f"💵 Ставка: <b>{bet:.2f}$</b>"
        anim1 = "Подготавливаем раунд…"
        anim2 = "Генерируем криптографический хэш…"
        anim3 = "Получаем seed…"
        final = (
            "Выбирай безопасные платформы и поднимайся выше!\n\n"
            "⚠️ Один неверный шаг — и башня падает."
        )
    else:
        title = "🧱 <b>Tower</b>"
        bet_line = f"💵 Bet: <b>{bet:.2f}$</b>"
        anim1 = "Preparing round…"
        anim2 = "Generating cryptographic hash…"
        anim3 = "Revealing seed…"
        final = (
            "Pick safe platforms and climb higher!\n\n"
            "⚠️ One wrong step — and everything collapses."
        )

    # -----------------------------
    #  АНИМАЦИЯ ЧЕСТНОСТИ
    # -----------------------------

    # Кадр 1 → старт
    await call.message.edit_text(
        f"{title}\n\n"
        f"{bet_line}\n\n"
        f"⏳ {anim1}"
    )
    await sleep(0.35)

    # Кадр 2 → показываем хэш
    await call.message.edit_text(
        f"{title}\n\n"
        f"{bet_line}\n\n"
        f"🔐 <b>Hash:</b>\n<code>{hash_value}</code>\n\n"
        f"{anim2}"
    )
    await sleep(0.45)

    # Кадр 3 → хэш + seed
    await call.message.edit_text(
        f"{title}\n\n"
        f"{bet_line}\n\n"
        f"🔐 <b>Hash:</b>\n<code>{hash_value}</code>\n"
        f"🔑 <b>Seed:</b>\n<code>{seed}</code>\n\n"
        f"{anim3}"
    )
    await sleep(0.45)

    # Финал → готоваTower + клавиатура
    await call.message.edit_text(
        f"{title}\n\n"
        f"{bet_line}\n\n"
        f"🔐 <b>Hash:</b>\n<code>{hash_value}</code>\n"
        f"🔑 <b>Seed:</b>\n<code>{seed}</code>\n\n"
        f"{final}",
        reply_markup=tower_keyboard(seed)
    )
