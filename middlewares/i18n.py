from aiogram import BaseMiddleware
from database.db import db


class LanguageMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):

        user = data.get("event_from_user")
        if not user:
            return await handler(event, data)

        user_id = user.id

        # Гарантируем, что запись существует
        await db.ensure_user(user_id)

        # Получаем язык
        row = await db.fetchone(
            "SELECT lang FROM users WHERE user_id=?",
            (user_id,)
        )

        lang = row[0] if row and row[0] else "ru"

        data["lang"] = lang

        return await handler(event, data)
