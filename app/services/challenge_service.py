"""
Сервис заданий — оркестрация прохождения челленджей.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.ai_service import AIService
from app.database.models import (
    AnswerType,
    BattleResult,
    BattleSession,
    Challenge,
    ChallengeAttempt,
    ChallengeCategory,
    ChallengeFormat,
    XPTransactionType,
)
from app.database.repositories import (
    AchievementRepository,
    AttemptRepository,
    ChallengeRepository,
    UserRepository,
    XPRepository,
)
from app.services.achievement_service import AchievementService
from app.services.xp_service import (
    DIFFICULTY_MULTIPLIERS,
    calculate_xp_for_attempt,
    get_level,
)

logger = logging.getLogger(__name__)


class ChallengeService:
    """Оркестратор прохождения заданий и битв."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.challenge_repo = ChallengeRepository(session)
        self.attempt_repo = AttemptRepository(session)
        self.user_repo = UserRepository(session)
        self.xp_repo = XPRepository(session)
        self.achievement_repo = AchievementRepository(session)
        self.achievement_service = AchievementService(session)
        self.ai_service = AIService()

    async def get_challenge(self, challenge_id: int) -> Challenge | None:
        return await self.challenge_repo.get_by_id(challenge_id)

    async def get_random_challenge(
        self, category: ChallengeCategory | None = None
    ) -> Challenge | None:
        return await self.challenge_repo.get_random(category)

    async def get_challenges_by_category(
        self, category: ChallengeCategory
    ) -> list[Challenge]:
        return await self.challenge_repo.get_by_category(category)

    async def get_options_list(self, challenge: Challenge) -> list[str] | None:
        """Парсим JSON список вариантов."""
        if not challenge.options:
            return None
        try:
            return json.loads(challenge.options)
        except Exception:
            return None

    async def submit_choice_answer(
        self,
        user_id: int,
        challenge: Challenge,
        selected_index: int,
        time_spent: int | None = None,
    ) -> dict:
        """Обработать ответ с выбором варианта."""
        correct_index = int(challenge.correct_answer) if challenge.correct_answer else -1
        is_correct = selected_index == correct_index
        score_percent = 100.0 if is_correct else 0.0

        return await self._finalize_attempt(
            user_id=user_id,
            challenge=challenge,
            user_answer=str(selected_index),
            selected_option=selected_index,
            is_correct=is_correct,
            score_percent=score_percent,
            feedback=challenge.explanation if is_correct else challenge.explanation,
            time_spent=time_spent,
            xp_multiplier=1.0,
        )

    async def submit_text_answer(
        self,
        user_id: int,
        challenge: Challenge,
        user_answer: str,
        time_spent: int | None = None,
    ) -> dict:
        """Обработать текстовый ответ с AI-оценкой."""
        # Ограничение длины ввода
        safe_answer = user_answer[:2000]

        criteria = {"criteria": ["completeness"], "min_score_to_pass": 1}
        if challenge.evaluation_criteria:
            raw_crit = challenge.evaluation_criteria
            if isinstance(raw_crit, str):
                try:
                    parsed = json.loads(raw_crit)
                    if isinstance(parsed, str):
                        try:
                            parsed = json.loads(parsed)
                        except Exception:
                            parsed = {"criteria": [parsed], "min_score_to_pass": 1}
                    if isinstance(parsed, dict):
                        criteria = parsed
                    elif isinstance(parsed, list):
                        criteria = {"criteria": parsed, "min_score_to_pass": 1}
                except Exception:
                    criteria = {"criteria": [raw_crit], "min_score_to_pass": 1}
            elif isinstance(raw_crit, dict):
                criteria = raw_crit

        result = await self.ai_service.evaluate_answer(
            challenge_description=challenge.description,
            user_answer=safe_answer,
            evaluation_criteria=criteria,
            reference_answer=challenge.explanation,
        )

        return await self._finalize_attempt(
            user_id=user_id,
            challenge=challenge,
            user_answer=safe_answer,
            selected_option=None,
            is_correct=result.is_correct,
            score_percent=result.score_percent,
            feedback=result.feedback,
            time_spent=time_spent,
            xp_multiplier=result.xp_multiplier,
        )

    async def _finalize_attempt(
        self,
        user_id: int,
        challenge: Challenge,
        user_answer: str | None,
        selected_option: int | None,
        is_correct: bool,
        score_percent: float,
        feedback: str | None,
        time_spent: int | None,
        xp_multiplier: float,
    ) -> dict:
        """Сохранить попытку, начислить XP, проверить достижения."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return {"error": "user_not_found"}

        # Проверяем, была ли уже вознаграждена попытка (идемпотентность)
        already_rewarded = await self.attempt_repo.has_rewarded_attempt(user_id, challenge.id)
        is_first_attempt = not already_rewarded
        xp_earned = 0

        if is_first_attempt:
            difficulty_mult = DIFFICULTY_MULTIPLIERS.get(challenge.difficulty.value, 1.0)
            xp_earned = calculate_xp_for_attempt(
                xp_base=challenge.xp_base,
                xp_max=challenge.xp_max,
                is_correct=is_correct,
                score_percent=score_percent,
                is_first_attempt=True,
                difficulty_multiplier=difficulty_mult,
                xp_multiplier=xp_multiplier,
            )

        # Сохраняем попытку
        attempt = await self.attempt_repo.create(
            user_id=user_id,
            challenge_id=challenge.id,
            user_answer=user_answer,
            selected_option=selected_option,
            is_correct=is_correct,
            score_percent=score_percent,
            xp_earned=xp_earned,
            feedback=feedback,
            time_spent_seconds=time_spent,
            is_first_attempt=is_first_attempt,
            xp_rewarded=is_first_attempt and xp_earned > 0,
        )

        level_up = False
        old_level = user.level

        # Начисляем XP транзакционно
        if xp_earned > 0 and is_first_attempt:
            xp_before = user.total_xp
            user.total_xp += xp_earned
            user.level = get_level(user.total_xp)
            level_up = user.level > old_level

            await self.xp_repo.create(
                user_id=user_id,
                amount=xp_earned,
                transaction_type=XPTransactionType.CHALLENGE_COMPLETE,
                description=f"Задание: {challenge.title}",
                xp_before=xp_before,
                xp_after=user.total_xp,
                reference_id=attempt.id,
            )

        # Обновляем статистику
        if is_first_attempt:
            await self.user_repo.increment_stats(
                user_id=user_id,
                challenges_completed=1,
                correct_answers=1 if is_correct else 0,
                total_answers=1,
            )

        await self.session.flush()

        # Проверяем достижения
        new_achievements = await self.achievement_service.check_and_grant(user_id, user)

        return {
            "attempt_id": attempt.id,
            "is_correct": is_correct,
            "score_percent": score_percent,
            "xp_earned": xp_earned,
            "is_first_attempt": is_first_attempt,
            "feedback": feedback,
            "explanation": challenge.explanation,
            "level_up": level_up,
            "new_level": user.level if level_up else None,
            "new_achievements": new_achievements,
            "total_xp": user.total_xp,
        }

    async def get_ai_response_for_battle(self, challenge: Challenge) -> str:
        """Получить ответ AI для режима Battle."""
        if challenge.ai_response:
            return challenge.ai_response  # Используем встроенный ответ

        # Запрашиваем у AI
        response = await self.ai_service.get_ai_response(challenge.description)
        return response.content
