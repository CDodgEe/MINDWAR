"""
AI Challenge Bot — Главная точка входа приложения.
Инициализирует Telegram-бота, базу данных, middleware, планировщик и роутеры.
"""

from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand, BotCommandScopeDefault

from app.config import get_settings
from app.database.seed import init_db, seed_data
from app.database.session import AsyncSessionFactory, engine
from app.handlers import get_all_routers
from app.middlewares.middlewares import DatabaseMiddleware, LoggingMiddleware, RateLimitMiddleware
from app.services.scheduler import setup_scheduler

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("ai_challenge_bot")


async def setup_bot_commands(bot: Bot) -> None:
    """Регистрация команд в меню Telegram."""
    commands = [
        BotCommand(command="start", description="🚀 Главное меню и старт"),
        BotCommand(command="battle", description="⚔️ AI Battle — вызов ИИ"),
        BotCommand(command="daily", description="🧠 Ежедневное испытание"),
        BotCommand(command="rating", description="🏆 Таблица лидеров"),
        BotCommand(command="profile", description="👤 Мой профиль и достижения"),
        BotCommand(command="help", description="❓ Как играть и правила"),
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
    logger.info("Bot commands registered successfully.")


async def create_storage(redis_url: str):
    """Инициализация хранилища FSM (Redis или Memory fallback)."""
    try:
        from redis.asyncio import from_url

        redis = from_url(redis_url, decode_responses=True)
        # Проверяем доступность Redis ping-запросом
        await asyncio.wait_for(redis.ping(), timeout=2.0)
        logger.info("Connected to Redis storage successfully.")
        return RedisStorage(redis=redis)
    except Exception as e:
        logger.warning(
            f"Redis unavailable ({e}). Falling back to in-memory MemoryStorage for FSM."
        )
        return MemoryStorage()


async def main() -> None:
    """Основной жизненный цикл приложения."""
    settings = get_settings()

    logger.info("========================================")
    logger.info("   ⚡ AI CHALLENGE BOT STARTING ⚡   ")
    logger.info("   «Think smarter. Create better. Challenge AI.»")
    logger.info("========================================")
    logger.info(f"AI Provider: {settings.ai_provider} (Model: {settings.ai_model})")
    logger.info(f"Database: {settings.database_url.split('@')[-1] if '@' in settings.database_url else 'configured'}")

    if not settings.bot_token:
        logger.error("BOT_TOKEN is not configured! Please provide BOT_TOKEN in .env file.")
        sys.exit(1)

    # 1. Инициализация базы данных и автоматический сидинг контента
    logger.info("Checking database schema and initial data...")
    try:
        await init_db()
        async with AsyncSessionFactory() as session:
            await seed_data(session)
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        sys.exit(1)

    # 2. Инициализация бота и хранилища
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    storage = await create_storage(settings.redis_url)
    dp = Dispatcher(storage=storage)

    # 3. Регистрация Middleware
    dp.update.outer_middleware(LoggingMiddleware())
    dp.update.outer_middleware(RateLimitMiddleware(max_requests=settings.max_requests_per_minute))
    dp.update.middleware(DatabaseMiddleware())

    # 4. Регистрация всех хендлеров
    for router in get_all_routers():
        dp.include_router(router)
    logger.info(f"Registered {len(get_all_routers())} router modules.")

    # 5. Установка команд Telegram
    await setup_bot_commands(bot)

    # 6. Запуск фонового планировщика
    scheduler = setup_scheduler(bot)
    scheduler.start()
    logger.info("Background APScheduler started.")

    # 7. Запуск бота (Polling или Webhook)
    try:
        if settings.bot_mode == "webhook":
            logger.info(f"Starting in Webhook mode on port {settings.webhook_port}...")
            # Webhook режим через aiohttp
            from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
            from aiohttp import web

            await bot.set_webhook(
                url=f"{settings.webhook_url}/webhook",
                secret_token=settings.webhook_secret or None,
                drop_pending_updates=True,
            )
            app = web.Application()
            webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot, secret_token=settings.webhook_secret or None)
            webhook_handler.register(app, path="/webhook")
            setup_application(app, dp, bot=bot)
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, host="0.0.0.0", port=settings.webhook_port)
            await site.start()
            logger.info(f"Webhook server is listening on port {settings.webhook_port}.")
            # Бесконечный цикл для удержания сервера
            while True:
                await asyncio.sleep(3600)
        else:
            logger.info("Starting in Long Polling mode...")
            await bot.delete_webhook(drop_pending_updates=True)
            await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Received termination signal.")
    finally:
        logger.info("Shutting down AI Challenge Bot...")
        scheduler.shutdown(wait=False)
        await bot.session.close()
        await engine.dispose()
        logger.info("Bot stopped cleanly. Goodbye!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
