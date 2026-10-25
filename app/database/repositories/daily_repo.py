"""Репозиторий ежедневных челленджей."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import DailyChallenge, UserDailyChallenge


class DailyChallengeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_date(self, date_str: str) -> DailyChallenge | None:
        result = await self.session.execute(
            select(DailyChallenge)
            .options(selectinload(DailyChallenge.challenge))
            .where(DailyChallenge.date == date_str)
        )
        return result.scalar_one_or_none()

    async def create(self, challenge_id: int, date_str: str) -> DailyChallenge:
        dc = DailyChallenge(challenge_id=challenge_id, date=date_str)
        self.session.add(dc)
        await self.session.flush()
        return dc

    async def get_or_create(self, date_str: str, challenge_id: int) -> DailyChallenge:
        dc = await self.get_by_date(date_str)
        if not dc:
            dc = await self.create(challenge_id, date_str)
        return dc

    async def get_user_completion(
        self, user_id: int, daily_challenge_id: int
    ) -> UserDailyChallenge | None:
        result = await self.session.execute(
            select(UserDailyChallenge).where(
                UserDailyChallenge.user_id == user_id,
                UserDailyChallenge.daily_challenge_id == daily_challenge_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_user_completion(
        self, user_id: int, daily_challenge_id: int
    ) -> UserDailyChallenge:
        udc = UserDailyChallenge(
            user_id=user_id,
            daily_challenge_id=daily_challenge_id,
        )
        self.session.add(udc)
        await self.session.flush()
        return udc
