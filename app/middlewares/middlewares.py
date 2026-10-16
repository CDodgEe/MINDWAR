"""
Middleware: инъекция сессии БД, rate limiting, логирование.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from app.config import get_settings
from app.database.session import AsyncSessionFactory

logger = logging.getLogger(__name__)
settings = get_settings()


class DatabaseMiddleware(BaseMiddleware):
    """Инъекция асинхронной сессии БД в каждый хендлер."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with AsyncSessionFactory() as session:
            data["session"] = session
            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise


class RateLimitMiddleware(BaseMiddleware):
    """Ограничение частоты запросов от одного пользователя."""

    def __init__(self, max_requests: int = 30, window_seconds: int = 60) -> None:
        self._requests: dict[int, list[float]] = defaultdict(list)
        self._max = max_requests
        self._window = window_seconds

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id = None
        if hasattr(event, "from_user") and event.from_user:
            user_id = event.from_user.id

        if user_id:
            now = time.time()
            window_start = now - self._window
            user_times = self._requests[user_id]

            # Очищаем старые записи
            self._requests[user_id] = [t for t in user_times if t > window_start]

            if len(self._requests[user_id]) >= self._max:
                logger.warning("Rate limit exceeded for user %s", user_id)
                from aiogram.types import CallbackQuery
                if isinstance(event, CallbackQuery):
                    await event.answer(
                        "⏳ Слишком много запросов. Подожди немного.",
                        show_alert=True,
                    )
                elif hasattr(event, "answer"):
                    await event.answer("⏳ Слишком много запросов. Подожди немного.")
                return None

            self._requests[user_id].append(now)

        return await handler(event, data)


class LoggingMiddleware(BaseMiddleware):
    """Логирование входящих событий (без персональных данных)."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id = None
        event_type = type(event).__name__

        if hasattr(event, "from_user") and event.from_user:
            user_id = event.from_user.id

        logger.debug("Event: %s, user: %s", event_type, user_id)
        return await handler(event, data)
