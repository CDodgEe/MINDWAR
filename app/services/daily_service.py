"""Сервис ежедневных заданий."""

from __future__ import annotations

import contextlib
import logging
import random
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    AnswerType,
    Challenge,
    UserDailyChallenge,
    XPTransactionType,
)
from app.database.repositories import (
    ChallengeRepository,
    DailyChallengeRepository,
    UserRepository,
    XPRepository,
)
from app.services.xp_service import get_level

logger = logging.getLogger(__name__)

DAILY_BONUS_XP = 20
STREAK_BONUS_XP = 10


class DailyChallengeService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.daily_repo = DailyChallengeRepository(session)
        self.challenge_repo = ChallengeRepository(session)
        self.user_repo = UserRepository(session)
        self.xp_repo = XPRepository(session)

    def _get_today_str(self) -> str:
        return datetime.now(tz=UTC).strftime("%Y-%m-%d")

    async def get_or_assign_daily(self) -> tuple[Challenge, str]:
        """Получить или назначить ежедневное задание. Возвращает (задание, дату)."""
        today = self._get_today_str()
        dc = await self.daily_repo.get_by_date(today)

        # Если задание уже было создано ранее без вариантов (например, текстовое), заменяем его на выбор
        if dc and (
            not dc.challenge
            or not dc.challenge.options
            or dc.challenge.answer_type != AnswerType.CHOICE
        ):
            eligible = await self.challenge_repo.get_daily_eligible()
            if eligible:
                challenge = random.choice(eligible)  # noqa: S311
                dc.challenge_id = challenge.id
                dc.challenge = challenge
                await self.session.flush()

        if not dc:
            # Выбираем случайное задание с вариантами ответа
            eligible = await self.challenge_repo.get_daily_eligible()
            if not eligible:
                raise ValueError("Нет доступных заданий для ежедневного вызова")
            challenge = random.choice(eligible)  # noqa: S311
            dc = await self.daily_repo.create(challenge.id, today)
            dc.challenge = challenge
            await self.session.flush()

        if not dc or not dc.challenge:
            raise ValueError("Не удалось получить ежедневное задание")

        return dc.challenge, today

    async def get_user_completion(
        self, user_id: int, date_str: str | None = None
    ) -> UserDailyChallenge | None:
        """Проверить, выполнил ли пользователь ежедневное задание."""
        today = date_str or self._get_today_str()
        dc = await self.daily_repo.get_by_date(today)
        if not dc:
            return None
        return await self.daily_repo.get_user_completion(user_id, dc.id)

    async def mark_daily_complete(self, user_id: int, xp_earned: int = 0) -> dict:  # noqa: ARG002
        """Отметить ежедневное задание выполненным и начислить бонус."""
        today = self._get_today_str()
        dc = await self.daily_repo.get_by_date(today)
        if not dc:
            with contextlib.suppress(Exception):
                await self.get_or_assign_daily()
                dc = await self.daily_repo.get_by_date(today)
        if not dc:
            return {"error": "no_daily_today"}

        # Идемпотентность: не начислять повторно
        existing = await self.daily_repo.get_user_completion(user_id, dc.id)
        if existing and existing.completed:
            return {"error": "already_completed", "xp_earned": 0}

        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return {"error": "user_not_found"}

        # Создаём или обновляем запись
        if not existing:
            udc = await self.daily_repo.create_user_completion(user_id, dc.id)
        else:
            udc = existing

        total_bonus = DAILY_BONUS_XP
        streak_bonus = 0

        # Обновляем серию дней
        now = datetime.now(tz=UTC)
        new_streak = await self._update_streak(user, now)

        if new_streak > 1:
            streak_bonus = min(STREAK_BONUS_XP * (new_streak - 1), 50)
            total_bonus += streak_bonus

        # Начисляем бонус XP
        xp_before = user.total_xp
        user.total_xp += total_bonus
        user.level = get_level(user.total_xp)

        await self.xp_repo.create(
            user_id=user_id,
            amount=total_bonus,
            transaction_type=XPTransactionType.DAILY_BONUS,
            description=f"Ежедневный бонус (серия: {new_streak} дней)",
            xp_before=xp_before,
            xp_after=user.total_xp,
        )

        udc.completed = True
        udc.xp_earned = total_bonus
        udc.completed_at = now

        await self.session.flush()

        return {
            "daily_bonus": DAILY_BONUS_XP,
            "streak_bonus": streak_bonus,
            "total_bonus": total_bonus,
            "new_streak": new_streak,
        }

    async def _update_streak(self, user, now: datetime) -> int:
        """Обновить серию дней активности."""
        if not user.last_active_date:
            user.streak_days = 1
            user.last_active_date = now
            return 1

        last = user.last_active_date
        if last.tzinfo is None:
            last = last.replace(tzinfo=UTC)

        days_diff = (now.date() - last.date()).days

        if days_diff == 0:
            return user.streak_days  # Уже был активен сегодня
        elif days_diff == 1:
            user.streak_days += 1
        else:
            user.streak_days = 1  # Серия прервана

        user.last_active_date = now
        return user.streak_days
