# handlers/menu.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from keyboards.menu import main_menu
from keyboards.language import language_keyboard
from database import db
router = Router()

@router.message(F.text == "/menu")
async def open_menu_msg(msg: Message, lang: str):
    await msg.answer(build_menu_text(lang), reply_markup=main_menu(lang))

@router.callback_query(F.data == "back")
async def open_menu_cb(call: CallbackQuery, lang: str):
    await call.message.edit_text(build_menu_text(lang), reply_markup=main_menu(lang))

@router.callback_query(F.data == "change_language")
async def change_language(call: CallbackQuery, lang: str):
    await call.message.edit_text(
        "Выберите язык / Choose language:",
        reply_markup=language_keyboard()
    )
@router.callback_query(F.data.startswith("lang_"))
async def change_language(call: CallbackQuery):
    lang_code = call.data.split("_")[1]   # ru / en
    user_id = call.from_user.id

    await db.ensure_user(user_id)         # <-- обязательно!

    await db.execute("""
        UPDATE users SET lang=?, updated_at=datetime('now')
        WHERE user_id=?
    """, (lang_code, user_id))

    await call.answer("Language updated.")
    # Обновляем меню, иначе используется старый lang
    from keyboards.menu import main_menu
    await call.message.edit_text("✔ Language updated.", reply_markup=main_menu(lang_code))



def build_menu_text(lang: str) -> str:
    if lang == "ru":
        return (
            "👋 <b>Добро пожаловать в Casino Bot</b>\n"
            "Выбирай, чем заняться прямо сейчас:\n"
            "• 🎮 Игры и быстрые режимы\n"
            "• ⚔️ Дуэли с живыми игроками\n"
            "• 🎁 Розыгрыши банка на команду\n"
            "• 📤 Вывод и 👥 Рефералы\n\n"
            "Нажми кнопку ниже, чтобы начать."
        )
    return (
        "👋 <b>Welcome to Casino Bot</b>\n"
        "Pick what you want to do now:\n"
        "• 🎮 Games and quick modes\n"
        "• ⚔️ Duels with real players\n"
        "• 🎁 Raffles for everyone who joins\n"
        "• 📤 Withdrawals and 👥 Referrals\n\n"
        "Use the buttons below to start."
    )
