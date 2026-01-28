from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from database.db import db

class UserInitMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if not getattr(event, "from_user", None):
            return await handler(event, data)

        user_id = event.from_user.id
        # Safe against races (INSERT OR IGNORE).
        await db.ensure_user(user_id)

        return await handler(event, data)
