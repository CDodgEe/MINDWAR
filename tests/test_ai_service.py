"""
Тесты AI-сервиса и провайдеров.
"""

from __future__ import annotations

import pytest

from app.ai.ai_service import AIService
from app.ai.mock_provider import MockAIProvider


@pytest.mark.asyncio
class TestAIService:
    async def test_mock_provider_response(self):
        """Mock провайдер возвращает детерминированный ответ."""
        provider = MockAIProvider()
        response = await provider.get_challenge_ai_response("Тестовое задание")
        assert response.content is not None
        assert "Ответ AI" in response.content
        assert response.provider == "mock"

    async def test_mock_provider_evaluate_empty_answer(self):
        """Оценка пустого ответа."""
        service = AIService()
        result = await service.evaluate_answer(
            challenge_description="Тестовое задание",
            user_answer="",
            evaluation_criteria={"criteria": []},
        )
        assert result.is_correct is False
        assert result.score_percent == 0.0

    async def test_mock_provider_evaluate_good_answer(self):
        """Оценка развернутого структурированного ответа."""
        provider = MockAIProvider()
        answer = (
            "1. Проанализируем исходные данные задачи.\n"
            "2. Выделим ключевые противоречия в логике рассуждения.\n"
            "3. Построим оптимальный алгоритм проверки: A -> B -> C.\n"
            "4. В результате получаем строго доказанное решение с учетом краевых случаев."
        )
        criteria = {
            "criteria": [
                {"name": "Логичность", "description": "Последовательность шагов", "weight": 1.0},
                {"name": "Полнота", "description": "Учет всех условий", "weight": 1.0},
            ],
            "min_score_to_pass": 1,
        }
        result = await provider.evaluate_open_answer(
            challenge_description="Решите логическую задачу",
            user_answer=answer,
            evaluation_criteria=criteria,
        )
        assert result.score_percent >= 50.0
        assert len(result.feedback) > 0
        assert result.is_correct is True
