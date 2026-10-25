"""Репозиторий заданий и попыток."""

from __future__ import annotations

import random

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    AnswerType,
    Challenge,
    ChallengeAttempt,
    ChallengeCategory,
    ChallengeFormat,
)


class ChallengeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, challenge_id: int) -> Challenge | None:
        result = await self.session.execute(
            select(Challenge).where(Challenge.id == challenge_id, Challenge.is_active == True)  # noqa
        )
        return result.scalar_one_or_none()

    async def get_by_external_id(self, external_id: str) -> Challenge | None:
        result = await self.session.execute(
            select(Challenge).where(Challenge.external_id == external_id)
        )
        return result.scalar_one_or_none()

    async def get_by_category(
        self, category: ChallengeCategory, limit: int = 20
    ) -> list[Challenge]:
        result = await self.session.execute(
            select(Challenge)
            .where(Challenge.category == category, Challenge.is_active == True)  # noqa
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_random(
        self,
        category: ChallengeCategory | None = None,
        challenge_format: ChallengeFormat | None = None,
        format: ChallengeFormat | None = None,  # noqa: A002
    ) -> Challenge | None:
        selected_fmt = challenge_format or format
        query = select(Challenge).where(Challenge.is_active == True)  # noqa: E712
        if category:
            query = query.where(Challenge.category == category)
        if selected_fmt:
            format_query = query.where(Challenge.format == selected_fmt)
            result = await self.session.execute(format_query)
            challenges = list(result.scalars().all())
            if challenges:
                return random.choice(challenges)  # noqa: S311
        result = await self.session.execute(query)
        challenges = list(result.scalars().all())
        return random.choice(challenges) if challenges else None  # noqa: S311

    async def get_all_active(self) -> list[Challenge]:
        result = await self.session.execute(
            select(Challenge).where(Challenge.is_active == True)  # noqa
        )
        return list(result.scalars().all())

    async def get_daily_eligible(self) -> list[Challenge]:
        result = await self.session.execute(
            select(Challenge).where(
                Challenge.is_active == True,  # noqa: E712
                Challenge.is_daily_eligible == True,  # noqa: E712
                Challenge.answer_type == AnswerType.CHOICE,
                Challenge.options.isnot(None),
            )
        )
        return list(result.scalars().all())

    async def count_active(self) -> int:
        result = await self.session.execute(
            select(Challenge).where(Challenge.is_active == True)  # noqa
        )
        return len(result.scalars().all())


class AttemptRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_user_attempt(
        self, user_id: int, challenge_id: int, first_only: bool = True
    ) -> ChallengeAttempt | None:
        query = select(ChallengeAttempt).where(
            and_(
                ChallengeAttempt.user_id == user_id,
                ChallengeAttempt.challenge_id == challenge_id,
            )
        )
        if first_only:
            query = query.where(ChallengeAttempt.is_first_attempt == True)  # noqa
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def has_rewarded_attempt(self, user_id: int, challenge_id: int) -> bool:
        result = await self.session.execute(
            select(ChallengeAttempt).where(
                and_(
                    ChallengeAttempt.user_id == user_id,
                    ChallengeAttempt.challenge_id == challenge_id,
                    ChallengeAttempt.xp_rewarded == True,  # noqa
                )
            )
        )
        return result.scalar_one_or_none() is not None

    async def create(
        self,
        user_id: int,
        challenge_id: int,
        user_answer: str | None,
        selected_option: int | None,
        is_correct: bool,
        score_percent: float,
        xp_earned: int,
        feedback: str | None = None,
        time_spent_seconds: int | None = None,
        is_first_attempt: bool = True,
        xp_rewarded: bool = False,
    ) -> ChallengeAttempt:
        attempt = ChallengeAttempt(
            user_id=user_id,
            challenge_id=challenge_id,
            user_answer=user_answer,
            selected_option=selected_option,
            is_correct=is_correct,
            score_percent=score_percent,
            xp_earned=xp_earned,
            feedback=feedback,
            time_spent_seconds=time_spent_seconds,
            is_first_attempt=is_first_attempt,
            xp_rewarded=xp_rewarded,
        )
        self.session.add(attempt)
        await self.session.flush()
        return attempt

    async def get_user_attempts(self, user_id: int, limit: int = 10) -> list[ChallengeAttempt]:
        result = await self.session.execute(
            select(ChallengeAttempt)
            .where(ChallengeAttempt.user_id == user_id)
            .order_by(ChallengeAttempt.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_user_category_completions(
        self, user_id: int, category: ChallengeCategory
    ) -> int:
        result = await self.session.execute(
            select(func.count(func.distinct(ChallengeAttempt.challenge_id)))
            .join(Challenge, Challenge.id == ChallengeAttempt.challenge_id)
            .where(
                ChallengeAttempt.user_id == user_id,
                Challenge.category == category,
                ChallengeAttempt.is_correct == True,  # noqa
            )
        )
        return result.scalar() or 0
