from aiogram import Router, F
from aiogram.types import CallbackQuery

from keyboards.deposit import deposit_keyboard
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.db import db

router = Router()


@router.callback_query(F.data == "profile")
async def open_profile(call: CallbackQuery, lang: str):
    user_id = call.from_user.id

    row = await db.fetchone("""
        SELECT 
            lang, balance, refs_total, refs_earned,
            games_played, games_won, games_lost
        FROM users 
        WHERE user_id = ?
    """, (user_id,))

    if not row:
        return await call.answer("Пользователь не найден", show_alert=True)

    user_lang, balance, refs_total, refs_earned, games_played, games_won, games_lost = row

    # -----------------------------
    # RU VERSION
    # -----------------------------
    if lang == "ru":
        text = (
            f"<b>👤 Профиль игрока</b>\n\n"
            f"<b>ID:</b> <code>{user_id}</code>\n"
            f"<b>Язык:</b> {user_lang}\n\n"

            f"<b>💳 Финансы</b>\n"
            f"Основной баланс: <b>{balance:.2f}$</b>\n"
            f"Доход с рефералов: <b>{refs_earned:.2f}$</b>\n"
            f"Рефералов привлечено: <b>{refs_total}</b>\n\n"

            f"<b>📊 Статистика игр</b>\n"
            f"Сыграно игр: <b>{games_played}</b>\n"
            f"Побед: <b>{games_won}</b>\n"
            f"Поражений: <b>{games_lost}</b>\n"
        )

    # -----------------------------
    # EN VERSION
    # -----------------------------
    else:
        text = (
            f"<b>👤 Player Profile</b>\n\n"
            f"<b>ID:</b> <code>{user_id}</code>\n"
            f"<b>Language:</b> {user_lang}\n\n"

            f"<b>💳 Finances</b>\n"
            f"Main balance: <b>{balance:.2f}$</b>\n"
            f"Referral income: <b>{refs_earned:.2f}$</b>\n"
            f"Total referrals: <b>{refs_total}</b>\n\n"

            f"<b>📊 Game Statistics</b>\n"
            f"Games played: <b>{games_played}</b>\n"
            f"Wins: <b>{games_won}</b>\n"
            f"Losses: <b>{games_lost}</b>\n"
        )

    kb = InlineKeyboardBuilder()
    kb.button(text="💳 Пополнить" if lang == "ru" else "💳 Deposit", callback_data="deposit")
    kb.button(text="📤 Вывод" if lang == "ru" else "📤 Withdraw", callback_data="withdraw_menu")
    kb.button(text="⬅️ Назад" if lang == "ru" else "⬅️ Back", callback_data="back")
    kb.adjust(2, 1)

    await call.message.edit_text(text, reply_markup=kb.as_markup())
