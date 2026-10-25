"""Репозиторий достижений."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import Achievement, UserAchievement


class AchievementRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_all(self) -> list[Achievement]:
        result = await self.session.execute(
            select(Achievement).where(Achievement.is_active == True)  # noqa
        )
        return list(result.scalars().all())

    async def get_user_achievements(self, user_id: int) -> list[UserAchievement]:
        result = await self.session.execute(
            select(UserAchievement)
            .options(selectinload(UserAchievement.achievement))
            .where(UserAchievement.user_id == user_id)
        )
        return list(result.scalars().all())

    async def has_achievement(self, user_id: int, achievement_code: str) -> bool:
        result = await self.session.execute(
            select(UserAchievement)
            .join(Achievement)
            .where(
                UserAchievement.user_id == user_id,
                Achievement.code == achievement_code,
            )
        )
        return result.scalar_one_or_none() is not None

    async def grant(self, user_id: int, achievement_id: int) -> UserAchievement:
        ua = UserAchievement(user_id=user_id, achievement_id=achievement_id)
        self.session.add(ua)
        await self.session.flush()
        return ua

    async def get_by_code(self, code: str) -> Achievement | None:
        result = await self.session.execute(select(Achievement).where(Achievement.code == code))
        return result.scalar_one_or_none()
