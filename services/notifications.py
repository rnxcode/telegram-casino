from __future__ import annotations

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties

from config import TOKEN, GAME_LOG_CHANNEL
from services.settings import get_game_log_channel


bot_instance: Bot | None = None


async def _get_bot() -> Bot:
    global bot_instance
    if bot_instance is None:
        bot_instance = Bot(
            token=TOKEN,
            default=DefaultBotProperties(parse_mode="HTML"),
        )
    return bot_instance


async def send_game_log(bot: Bot | None, text: str) -> None:
    channel = await get_game_log_channel()
    if not channel:
        return
    try:
        client = bot or await _get_bot()
        await client.send_message(channel, text, disable_web_page_preview=True)
    except Exception:
        pass
