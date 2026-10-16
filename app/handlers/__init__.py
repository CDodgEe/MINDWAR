"""
Пакет хендлеров AI Challenge Bot.
Собирает все роутеры в единый список для регистрации в Dispatcher.
"""

from __future__ import annotations

from aiogram import Router

from app.handlers import admin, challenges, daily, help, leaderboard, profile, start


def get_all_routers() -> list[Router]:
    """Возвращает список всех роутеров бота в порядке приоритета обработки."""
    return [
        admin.router,
        start.router,
        daily.router,
        challenges.router,
        leaderboard.router,
        profile.router,
        help.router,
    ]


__all__ = [
    "admin",
    "challenges",
    "daily",
    "get_all_routers",
    "help",
    "leaderboard",
    "profile",
    "start",
]
