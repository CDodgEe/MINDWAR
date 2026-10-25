"""Фильтры для хендлеров."""

from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject

from app.config import get_settings

settings = get_settings()


class AdminFilter(BaseFilter):
    """Проверка, является ли пользователь администратором."""

    async def __call__(self, event: TelegramObject) -> bool:
        user = getattr(event, "from_user", None)
        if not user:
            return False
        return user.id in settings.admin_ids
