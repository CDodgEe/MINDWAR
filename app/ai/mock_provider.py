"""
Mock AI провайдер — для тестирования и работы без внешнего API.
Возвращает детерминированные ответы без обращения к сети.
"""

from __future__ import annotations

import json
import re

from app.ai.base import AIEvaluationResult, AIResponse, BaseAIProvider


class MockAIProvider(BaseAIProvider):
    """Тестовый провайдер — работает без внешнего API."""

    async def get_challenge_ai_response(
        self, challenge_description: str  # noqa: ARG002
    ) -> AIResponse:
        return AIResponse(
            content=(
                "🤖 *Ответ AI:* Это задание требует аналитического мышления. "
                "Я обработал условия и предлагаю следующее решение: "
                "необходимо последовательно рассмотреть все данные, "
                "применить логические операции и прийти к выводу."
            ),
            provider="mock",
            model=None,
            tokens_used=0,
        )

    async def evaluate_open_answer(
        self,
        challenge_description: str,  # noqa: ARG002
        user_answer: str,
        evaluation_criteria: dict,
        reference_answer: str | None = None,  # noqa: ARG002
    ) -> AIEvaluationResult:
        if isinstance(evaluation_criteria, str):
            try:
                evaluation_criteria = json.loads(evaluation_criteria)
                if isinstance(evaluation_criteria, str):
                    evaluation_criteria = json.loads(evaluation_criteria)
            except Exception:
                evaluation_criteria = {"criteria": [evaluation_criteria], "min_score_to_pass": 1}
        if not isinstance(evaluation_criteria, dict):
            evaluation_criteria = {"criteria": ["completeness"], "min_score_to_pass": 1}

        criteria = evaluation_criteria.get("criteria", [])
        if isinstance(criteria, str):
            criteria = [criteria]
        min_score = evaluation_criteria.get("min_score_to_pass", 1)

        # Простая эвристика: оцениваем по длине и ключевым словам
        clean_answer = user_answer.strip()
        answer_length = len(clean_answer)

        criteria_scores = {
            c.get("name", f"criterion_{i}") if isinstance(c, dict) else str(c): 0.0
            for i, c in enumerate(criteria)
        }

        # Слишком короткий ответ
        if answer_length < 20:
            for k in criteria_scores:
                criteria_scores[k] = 0.1
            return AIEvaluationResult(
                score_percent=15.0,
                is_correct=False,
                feedback="💡 Ответ слишком короткий. Постарайся дать более развёрнутый и аргументированный ответ.",
                criteria_scores=criteria_scores,
                xp_multiplier=0.2,
            )

        # Базовый балл по длине ответа
        if answer_length < 50:
            base_score = 0.3
        elif answer_length < 100:
            base_score = 0.5
        elif answer_length < 300:
            base_score = 0.7
        else:
            base_score = 0.85

        # Проверяем наличие структуры (числа, пункты)
        has_structure = bool(re.search(r"\d+[.)]\s|\n[-•]", clean_answer))
        if has_structure:
            base_score = min(1.0, base_score + 0.1)

        # Рассчитываем количество выполненных критериев
        fulfilled_criteria = round(len(criteria) * base_score) if criteria else 0
        score_percent = (fulfilled_criteria / max(len(criteria), 1)) * 100

        is_correct = fulfilled_criteria >= min_score and base_score >= 0.5

        criteria_scores = {
            c.get("name", f"criterion_{i}") if isinstance(c, dict) else str(c): base_score
            for i, c in enumerate(criteria)
        }

        if is_correct:
            feedback = (
                f"✅ Хороший ответ! Ты затронул {fulfilled_criteria} из {len(criteria)} "
                f"ключевых аспектов задания. Продолжай развивать навык структурированного мышления."
            )
            xp_multiplier = 0.8 + base_score * 0.5
        else:
            feedback = (
                "💡 Ответ принят. Для максимального балла постарайся структурировать "
                "мысли: укажи конкретные пункты и обоснуй каждый из них."
            )
            xp_multiplier = 0.3

        return AIEvaluationResult(
            score_percent=score_percent,
            is_correct=is_correct,
            feedback=feedback,
            criteria_scores=criteria_scores,
            xp_multiplier=min(1.5, xp_multiplier),
        )

    async def is_available(self) -> bool:
        return True
