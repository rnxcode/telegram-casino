# handlers/referrals.py
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from database.db import db

router = Router()


@router.callback_query(F.data == "ref_menu")
async def ref_menu(call: CallbackQuery, lang: str):
    user_id = call.from_user.id

    row = await db.fetchone("""
        SELECT refs_total, refs_earned, referred_by 
        FROM users 
        WHERE user_id = ?
    """, (user_id,))

    if row:
        refs_total, refs_earned, referred_by = row
        ref_link = f"https://t.me/vornexBot?start=ref{user_id}"

        if lang == "ru":
            text = (
                f"<b>🤝 Реферальная система</b>\n\n"
                f"👥 Приглашено: <b>{refs_total}</b>\n"
                f"💰 Заработано: <b>{refs_earned:.2f}$</b>\n\n"
                f"<b>🔗 Ваша ссылка:</b>\n{ref_link}\n\n"
                f"Приглашайте друзей и получайте:\n"
                f"• 10% с их проигрышей в играх\n"
            )
        else:
            text = (
                f"<b>🤝 Referral system</b>\n\n"
                f"👥 Invited: <b>{refs_total}</b>\n"
                f"💰 Earned: <b>{refs_earned:.2f}$</b>\n\n"
                f"<b>🔗 Your link:</b>\n{ref_link}\n\n"
                f"Invite friends and earn:\n"
                f"• 10% of their in-game losses\n"
            )

    else:
        text = "❌ Ошибка загрузки данных" if lang == "ru" else "❌ Error loading data"

    # Кнопка назад
    back_label = "⬅️ Назад" if lang == "ru" else "⬅️ Back"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=back_label, callback_data="dep_back")]]
    )

    await call.message.edit_text(text, reply_markup=keyboard)
