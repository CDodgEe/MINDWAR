"""Репозиторий пользователей."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import User, UserSettings


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.session.execute(
            select(User)
            .options(selectinload(User.settings))
            .where(User.id == user_id, User.is_deleted == False)  # noqa: E712
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        user_id: int,
        display_name: str,
        username: str | None = None,
        language_code: str = "ru",
    ) -> User:
        user = User(
            id=user_id,
            display_name=display_name,
            username=username,
            language_code=language_code,
        )
        settings = UserSettings(user_id=user_id)
        self.session.add(user)
        self.session.add(settings)
        await self.session.flush()
        return user

    async def get_or_create(
        self,
        user_id: int,
        display_name: str,
        username: str | None = None,
        language_code: str = "ru",
    ) -> tuple[User, bool]:
        user = await self.get_by_id(user_id)
        if user:
            return user, False
        user = await self.create(user_id, display_name, username, language_code)
        return user, True

    async def update_display_name(self, user_id: int, display_name: str) -> None:
        await self.session.execute(
            update(User).where(User.id == user_id).values(display_name=display_name)
        )

    async def update_streak(self, user_id: int, new_streak: int, date: datetime) -> None:
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(streak_days=new_streak, last_active_date=date)
        )

    async def increment_stats(
        self,
        user_id: int,
        challenges_completed: int = 0,
        battles_won: int = 0,
        battles_total: int = 0,
        correct_answers: int = 0,
        total_answers: int = 0,
    ) -> None:
        user = await self.get_by_id(user_id)
        if not user:
            return
        user.challenges_completed += challenges_completed
        user.battles_won += battles_won
        user.battles_total += battles_total
        user.correct_answers += correct_answers
        user.total_answers += total_answers

    async def soft_delete(self, user_id: int) -> None:
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(is_deleted=True, display_name="[Удалён]", username=None)
        )

    async def get_top_users(self, limit: int = 10, offset: int = 0) -> list[User]:
        result = await self.session.execute(
            select(User)
            .where(User.is_deleted == False, User.is_banned == False)  # noqa: E712
            .order_by(User.total_xp.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_user_rank(self, user_id: int) -> int:
        result = await self.session.execute(
            select(User.total_xp).where(User.id == user_id)
        )
        user_xp = result.scalar_one_or_none()
        if user_xp is None:
            return 0
        rank_result = await self.session.execute(
            select(User.id)
            .where(
                User.is_deleted == False,  # noqa: E712
                User.is_banned == False,  # noqa: E712
                User.total_xp > user_xp,
            )
        )
        return len(rank_result.scalars().all()) + 1
