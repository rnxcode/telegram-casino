# handlers/start.py - с исправленной проверкой подписки
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from keyboards.language import language_keyboard
from keyboards.menu import main_menu
from database.db import db
from services.settings import get_channels

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    args = message.text.split()
    user_id = message.from_user.id

    # Проверяем: новый ли юзер
    row = await db.fetchone("SELECT 1 FROM users WHERE user_id=?", (user_id,))
    is_new = row is None

    # Обработка реферальной ссылки
    if is_new and len(args) > 1 and args[1].startswith("ref"):
        try:
            inviter_id = int(args[1][3:])
            if inviter_id != user_id:
                await db.execute(
                    "INSERT OR REPLACE INTO referrals (user_id, referred_by) VALUES (?,?)",
                    (user_id, inviter_id)
                )
                await db.execute("""
                    INSERT INTO referral_stats (user_id, total_refs, earned)
                    VALUES (?,1,0)
                    ON CONFLICT(user_id) DO UPDATE SET total_refs = total_refs + 1
                    """, (inviter_id,))
                await db.execute(
                    "UPDATE users SET bonus = bonus + 1 WHERE user_id=?",
                    (inviter_id,)
                )
        except:
            pass

    # Проверяем язык пользователя
    row = await db.fetchone(
        "SELECT lang FROM users WHERE user_id=?",
        (user_id,)
    )

    # Обработка приглашения в дуэль
    duel_id = None
    if len(args) > 1 and args[1].startswith("duel_"):
        try:
            duel_id = int(args[1].split("_")[1])
        except Exception:
            duel_id = None

    # Если язык ещё не выбран → показываем меню выбора
    if row is None:
        await message.answer(
            "Выберите язык / Choose language:",
            reply_markup=language_keyboard()
        )
        return

    # Если язык есть — проверяем подписку
    lang = row[0]

    # Проверяем подписку сразу после старта
    bot = message.bot
    not_subscribed = []
    channel_info = []

    channels = await get_channels()
    for channel in channels:
        try:
            try:
                chat_id = int(channel)
            except ValueError:
                chat_id = channel

            member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                not_subscribed.append(channel)

                # Получаем информацию о канале
                try:
                    chat_info = await bot.get_chat(chat_id)
                    if chat_info.username:
                        channel_link = f"https://t.me/{chat_info.username}"
                    elif chat_info.invite_link:
                        channel_link = chat_info.invite_link
                    else:
                        channel_link = f"https://t.me/c/{str(chat_id).replace('-100', '')}"
                    channel_name = chat_info.title or f"Канал {channel}"
                except:
                    channel_link = f"https://t.me/c/{str(channel).replace('-100', '')}" if str(channel).startswith(
                        '-100') else f"https://t.me/{channel}"
                    channel_name = f"Канал {channel}"

                channel_info.append({
                    'id': channel,
                    'name': channel_name,
                    'link': channel_link
                })
        except Exception as e:
            print(f"Ошибка при проверке подписки: {e}")

    # Если не подписан - показываем запрос подписки
    if not_subscribed:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

        if lang == "ru":
            text = "📢 Для использования бота необходимо подписаться на наши каналы:\n\n"
            for info in channel_info:
                text += f"• {info['name']}\n"
            text += "\nПосле подписки нажмите кнопку 'Проверить подписку' ✅"
        else:
            text = "📢 To use the bot you need to subscribe to our channels:\n\n"
            for info in channel_info:
                text += f"• {info['name']}\n"
            text += "\nAfter subscribing, click the 'Check subscription' button ✅"

        buttons = []
        for info in channel_info:
            buttons.append([InlineKeyboardButton(
                text=f"📢 Подписаться" if lang == "ru" else f"📢 Subscribe",
                url=info['link']
            )])

        buttons.append([InlineKeyboardButton(
            text="✅ Проверить подписку" if lang == "ru" else "✅ Check subscription",
            callback_data="check_subscription"
        )])

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.answer(text, reply_markup=keyboard)
        return

    # Если подписан - показываем меню
    if duel_id:
        duel = await db.get_duel(duel_id)
        if duel and duel["status"] == "waiting":
            from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
            game = "Кубик" if duel["game"] == "dice" else "Рулетка 🎯"
            game_en = "Dice" if duel["game"] == "dice" else "Darts 🎯"
            text = (
                f"⚔️ Приглашение в дуэль\n"
                f"Игра: {game}\n"
                f"Ставка: {duel['bet']:.2f}$\n"
                "Готовы вступить?"
            ) if lang == "ru" else (
                f"⚔️ Duel invite\n"
                f"Game: {game_en}\n"
                f"Stake: {duel['bet']:.2f}$\n"
                "Join?"
            )
            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="✅ Вступить" if lang == "ru" else "✅ Join", callback_data=f"duel_join:{duel_id}")],
                    [InlineKeyboardButton(text="⬅️ Меню" if lang == "ru" else "⬅️ Menu", callback_data="back")],
                ]
            )
            await message.answer(text, reply_markup=kb)
            return

    text = "Добро пожаловать в Casino Bot 🎰" if lang == "ru" else "Welcome to Casino Bot 🎰"
    await message.answer(text, reply_markup=main_menu(lang))


@router.callback_query(F.data.startswith("lang_"))
async def set_language(call: CallbackQuery):
    lang = call.data.split("_")[1]
    user_id = call.from_user.id

    # гарантируем существование строки
    await db.ensure_user(user_id)

    # безопасно обновляем язык
    await db.execute(
        "UPDATE users SET lang=?, updated_at=datetime('now') WHERE user_id=?",
        (lang, user_id)
    )
    # Сразу проверяем подписку после выбора языка
    user_id = call.from_user.id
    bot = call.bot
    not_subscribed = []
    channel_info = []

    channels = await get_channels()
    for channel in channels:
        try:
            try:
                chat_id = int(channel)
            except ValueError:
                chat_id = channel

            member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                not_subscribed.append(channel)

                try:
                    chat_info = await bot.get_chat(chat_id)
                    if chat_info.username:
                        channel_link = f"https://t.me/{chat_info.username}"
                    elif chat_info.invite_link:
                        channel_link = chat_info.invite_link
                    else:
                        channel_link = f"https://t.me/c/{str(chat_id).replace('-100', '')}"
                    channel_name = chat_info.title or f"Канал {channel}"
                except:
                    channel_link = f"https://t.me/c/{str(channel).replace('-100', '')}" if str(channel).startswith(
                        '-100') else f"https://t.me/{channel}"
                    channel_name = f"Канал {channel}"

                channel_info.append({
                    'id': channel,
                    'name': channel_name,
                    'link': channel_link
                })
        except:
            pass

    # Если не подписан
    if not_subscribed:
        if lang == "ru":
            text = "📢 Для использования бота необходимо подписаться на наши каналы:\n\n"
            for info in channel_info:
                text += f"• {info['name']}\n"
            text += "\nПосле подписки нажмите кнопку 'Проверить подписку' ✅"
        else:
            text = "📢 To use the bot you need to subscribe to our channels:\n\n"
            for info in channel_info:
                text += f"• {info['name']}\n"
            text += "\nAfter subscribing, click the 'Check subscription' button ✅"

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        buttons = []
        for info in channel_info:
            buttons.append([InlineKeyboardButton(
                text=f"📢 Подписаться" if lang == "ru" else f"📢 Subscribe",
                url=info['link']
            )])

        buttons.append([InlineKeyboardButton(
            text="✅ Проверить подписку" if lang == "ru" else "✅ Check subscription",
            callback_data="check_subscription"
        )])

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await call.message.edit_text(text, reply_markup=keyboard)
        return

    # Если подписан
    text = (
        "Язык установлен: Русский 🇷🇺\n\nДобро пожаловать в Casino Bot 🎰"
        if lang == "ru"
        else "Language set: English 🇬🇧\n\nWelcome to Casino Bot 🎰"
    )
    await call.message.edit_text(text, reply_markup=main_menu(lang))


@router.callback_query(F.data == "check_subscription")
async def check_subscription(call: CallbackQuery):
    user_id = call.from_user.id
    bot = call.bot

    # Получаем язык пользователя
    row = await db.fetchone("SELECT lang FROM users WHERE user_id=?", (user_id,))
    if not row:
        return

    lang = row[0]

    # Проверяем подписку
    not_subscribed = []
    channels = await get_channels()
    for channel in channels:
        try:
            try:
                chat_id = int(channel)
            except ValueError:
                chat_id = channel

            member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                not_subscribed.append(channel)
        except Exception as e:
            print(f"Ошибка проверки подписки: {e}")
            not_subscribed.append(channel)

    # Если всё ещё не подписан
    if not_subscribed:
        # Получаем информацию о каналах для ссылок
        channel_info = []
        for channel in not_subscribed:
            try:
                try:
                    chat_id = int(channel)
                except ValueError:
                    chat_id = channel

                chat_info = await bot.get_chat(chat_id)
                if chat_info.username:
                    channel_link = f"https://t.me/{chat_info.username}"
                elif chat_info.invite_link:
                    channel_link = chat_info.invite_link
                else:
                    channel_link = f"https://t.me/c/{str(chat_id).replace('-100', '')}"
                channel_name = chat_info.title or f"Канал {channel}"
            except:
                channel_link = f"https://t.me/c/{str(channel).replace('-100', '')}" if str(channel).startswith(
                    '-100') else f"https://t.me/{channel}"
                channel_name = f"Канал {channel}"

            channel_info.append({
                'name': channel_name,
                'link': channel_link
            })

        if lang == "ru":
            text = "❌ Вы всё ещё не подписаны на все каналы!\n\n"
            for info in channel_info:
                text += f"• {info['name']}\n"
        else:
            text = "❌ You are still not subscribed to all channels!\n\n"
            for info in channel_info:
                text += f"• {info['name']}\n"

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        buttons = []
        for info in channel_info:
            buttons.append([InlineKeyboardButton(
                text=f"📢 Подписаться" if lang == "ru" else f"📢 Subscribe",
                url=info['link']
            )])

        buttons.append([InlineKeyboardButton(
            text="✅ Проверить подписку" if lang == "ru" else "✅ Check subscription",
            callback_data="check_subscription"
        )])

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await call.message.edit_text(text, reply_markup=keyboard)
        return

    # Если подписан на все каналы
    text = "✅ Отлично! Вы подписаны на все каналы!\n\n"
    text += "Добро пожаловать в Casino Bot 🎰" if lang == "ru" else "Welcome to Casino Bot 🎰"

    from keyboards.menu import main_menu
    await call.message.edit_text(text, reply_markup=main_menu(lang))
