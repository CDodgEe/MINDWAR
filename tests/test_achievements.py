"""
Тесты сервиса достижений.
"""

from __future__ import annotations

import pytest

from app.database.models import Achievement, User
from app.services.achievement_service import AchievementService


@pytest.mark.asyncio
class TestAchievementConditions:
    async def test_streak_condition(self):
        """Проверка условия по дням серии."""
        service = AchievementService(session=None)
        user = User(
            id=12345,
            display_name="Player",
            streak_days=7,
            correct_answers=1,
            challenges_completed=1,
            level=1,
        )
        ach_7 = Achievement(
            code="seven_day_streak",
            name="7 дней",
            description="",
            condition_type="streak_days",
            condition_value="7",
        )
        ach_14 = Achievement(
            code="fourteen_day_streak",
            name="14 дней",
            description="",
            condition_type="streak_days",
            condition_value="14",
        )
        assert await service._check_condition(user, ach_7) is True
        assert await service._check_condition(user, ach_14) is False

    async def test_correct_answers_condition(self):
        """Проверка условия по количеству правильных ответов."""
        service = AchievementService(session=None)
        user = User(
            id=12345,
            display_name="Player",
            streak_days=1,
            correct_answers=10,
            challenges_completed=15,
            level=2,
        )
        ach = Achievement(
            code="first_win",
            name="Первая победа",
            description="",
            condition_type="correct_answers_total",
            condition_value="1",
        )
        assert await service._check_condition(user, ach) is True
