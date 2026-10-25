"""AI Service — единая точка входа для всех AI-операций."""

from __future__ import annotations

import logging

from app.ai.base import AIEvaluationResult, AIResponse, BaseAIProvider
from app.ai.mock_provider import MockAIProvider
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_provider: BaseAIProvider | None = None


def get_ai_provider() -> BaseAIProvider:
    global _provider
    if _provider is None:
        if settings.ai_provider == "mock" or not settings.ai_api_key:
            _provider = MockAIProvider()
            logger.info("AI provider: Mock (no API key configured)")
        else:
            from app.ai.llm_provider import LLMProvider

            _provider = LLMProvider()
            logger.info("AI provider: LLM (%s)", settings.ai_model)
    return _provider


class AIService:
    """Сервис для работы с AI. Все обращения к AI проходят через этот класс."""

    def __init__(self) -> None:
        self._provider = get_ai_provider()

    async def get_ai_response(self, challenge_description: str) -> AIResponse:
        """Получить ответ AI на задание."""
        try:
            return await self._provider.get_challenge_ai_response(challenge_description)
        except Exception as e:
            logger.error("AI response failed: %s", e)
            return AIResponse(
                content="🤖 AI анализирует задание... (автономный режим)",
                provider="fallback",
            )

    async def evaluate_answer(
        self,
        challenge_description: str,
        user_answer: str,
        evaluation_criteria: dict,
        reference_answer: str | None = None,
    ) -> AIEvaluationResult:
        """Оценить открытый ответ пользователя."""
        if not user_answer or not user_answer.strip():
            return AIEvaluationResult(
                score_percent=0.0,
                is_correct=False,
                feedback="Пустой ответ не может быть оценён.",
                criteria_scores={},
                xp_multiplier=0.0,
            )

        try:
            return await self._provider.evaluate_open_answer(
                challenge_description, user_answer, evaluation_criteria, reference_answer
            )
        except Exception as e:
            logger.error("AI evaluation failed: %s", e)
            # Fallback: базовая оценка
            fallback = MockAIProvider()
            return await fallback.evaluate_open_answer(
                challenge_description, user_answer, evaluation_criteria, reference_answer
            )

    async def is_available(self) -> bool:
        return await self._provider.is_available()
