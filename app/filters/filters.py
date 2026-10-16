"""Фильтры для хендлеров."""

from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import Message

from app.config import get_settings

settings = get_settings()


class AdminFilter(BaseFilter):
    """Проверка, является ли пользователь администратором."""

    async def __call__(self, message: Message) -> bool:
        if not message.from_user:
            return False
        return message.from_user.id in settings.admin_ids
