"""
Базовый интерфейс AI-провайдера.
Все провайдеры реализуют этот интерфейс.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AIEvaluationResult:
    """Структурированный результат оценки открытого ответа."""

    score_percent: float  # 0.0 - 100.0
    is_correct: bool
    feedback: str
    criteria_scores: dict[str, float]  # критерий -> оценка 0-1
    xp_multiplier: float  # множитель для XP (0.5 - 1.5)


@dataclass
class AIResponse:
    """Ответ AI на задание."""

    content: str
    provider: str
    model: str | None = None
    tokens_used: int = 0


class BaseAIProvider(ABC):
    """Базовый интерфейс для всех AI-провайдеров."""

    @abstractmethod
    async def get_challenge_ai_response(self, challenge_description: str) -> AIResponse:
        """Получить ответ AI на задание (для Human First режима)."""
        ...

    @abstractmethod
    async def evaluate_open_answer(
        self,
        challenge_description: str,
        user_answer: str,
        evaluation_criteria: dict,
        reference_answer: str | None = None,
    ) -> AIEvaluationResult:
        """Оценить открытый ответ пользователя по критериям."""
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """Проверить доступность провайдера."""
        ...
