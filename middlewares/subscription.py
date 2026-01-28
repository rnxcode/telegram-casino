# middlewares/subscription.py
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from database.db import db
from services.settings import get_channels


class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Message | CallbackQuery,
            data: Dict[str, Any]
    ) -> Any:
        # Исключаем команду /start и выбор языка
        if isinstance(event, Message):
            if event.text:
                if event.text.startswith('/start'):
                    return await handler(event, data)
                elif event.text.startswith('/lang'):
                    return await handler(event, data)

        if isinstance(event, CallbackQuery) and event.data:
            if event.data.startswith('lang_'):
                return await handler(event, data)

        user_id = event.from_user.id

        # Проверяем, есть ли пользователь в БД
        user = await db.fetchone("SELECT lang FROM users WHERE user_id=?", (user_id,))

        # Если пользователя нет в БД, пропускаем (он ещё не выбрал язык)
        if not user:
            return await handler(event, data)

        # Проверяем подписку на все каналы
        bot = data['bot']
        not_subscribed = []
        channel_info = []  # Для хранения информации о каналах (название, ссылка)

        channels = await get_channels()
        for channel in channels:
            try:
                # Преобразуем ID в int если это числовой ID
                try:
                    chat_id = int(channel)
                except ValueError:
                    chat_id = channel  # Оставляем как строку (для username)

                member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
                if member.status not in ['member', 'administrator', 'creator']:
                    not_subscribed.append(channel)

                    # Получаем информацию о канале для ссылки
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
                print(f"Ошибка проверки подписки: {e}")
                not_subscribed.append(channel)
                channel_info.append({
                    'id': channel,
                    'name': f"Канал {channel}",
                    'link': f"https://t.me/c/{str(channel).replace('-100', '')}" if str(channel).startswith(
                        '-100') else f"https://t.me/{channel}"
                })

        # Если не подписан на какие-то каналы
        if not_subscribed:
            lang = user[0]
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

            if isinstance(event, Message):
                await event.answer(text, reply_markup=keyboard)
            else:
                await event.message.edit_text(text, reply_markup=keyboard)
            return

        return await handler(event, data)
