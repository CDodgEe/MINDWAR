"""
Сервис достижений — автоматическая проверка и выдача.
"""

from __future__ import annotations

import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Achievement, User, XPTransactionType
from app.database.repositories import AchievementRepository, XPRepository
from app.services.xp_service import get_level

logger = logging.getLogger(__name__)


class AchievementService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.achievement_repo = AchievementRepository(session)
        self.xp_repo = XPRepository(session)

    async def check_and_grant(self, user_id: int, user: User) -> list[Achievement]:
        """Проверить все достижения и выдать незаработанные. Возвращает список новых."""
        all_achievements = await self.achievement_repo.get_all()
        new_achievements = []

        for achievement in all_achievements:
            if await self.achievement_repo.has_achievement(user_id, achievement.code):
                continue

            earned = await self._check_condition(user, achievement)
            if earned:
                await self.achievement_repo.grant(user_id, achievement.id)
                # Начислить XP за достижение
                if achievement.xp_reward > 0:
                    xp_before = user.total_xp
                    user.total_xp += achievement.xp_reward
                    user.level = get_level(user.total_xp)
                    await self.xp_repo.create(
                        user_id=user_id,
                        amount=achievement.xp_reward,
                        transaction_type=XPTransactionType.ACHIEVEMENT_BONUS,
                        description=f"Достижение: {achievement.name}",
                        xp_before=xp_before,
                        xp_after=user.total_xp,
                    )
                new_achievements.append(achievement)
                logger.info("Achievement granted: user=%s, code=%s", user_id, achievement.code)

        return new_achievements

    async def _check_condition(self, user: User, achievement: Achievement) -> bool:
        """Проверить условие достижения."""
        try:
            ctype = achievement.condition_type
            cval = achievement.condition_value

            if ctype == "correct_answers_total":
                return user.correct_answers >= int(cval or 0)

            elif ctype == "challenges_completed":
                return user.challenges_completed >= int(cval or 0)

            elif ctype == "streak_days":
                return user.streak_days >= int(cval or 0)

            elif ctype == "level_reached":
                return user.level >= int(cval or 0)

            elif ctype == "category_correct":
                data = json.loads(cval) if cval else {}
                from app.database.models import ChallengeCategory
                from app.database.repositories import AttemptRepository

                repo = AttemptRepository(self.session)
                category = ChallengeCategory(data.get("category", "logic"))
                count = await repo.count_user_category_completions(user.id, category)
                return count >= data.get("count", 1)

            elif ctype == "daily_completed":
                from sqlalchemy import select

                from app.database.models import UserDailyChallenge

                result = await self.session.execute(
                    select(UserDailyChallenge).where(
                        UserDailyChallenge.user_id == user.id,
                        UserDailyChallenge.completed == True,  # noqa
                    )
                )
                completed_count = len(result.scalars().all())
                return completed_count >= int(cval or 0)

            elif ctype == "comeback":
                # Проверяем: последние 2 попытки = неверная, потом верная
                from app.database.repositories import AttemptRepository

                repo = AttemptRepository(self.session)
                attempts = await repo.get_user_attempts(user.id, limit=2)
                if len(attempts) >= 2:
                    return attempts[0].is_correct and not attempts[1].is_correct

        except Exception as e:
            logger.warning("Achievement check error: %s", e)

        return False
