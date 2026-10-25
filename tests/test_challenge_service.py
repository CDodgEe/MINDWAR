"""
Тесты сервиса заданий (ChallengeService).
"""

from __future__ import annotations

import json

from app.database.models import (
    AnswerType,
    Challenge,
    ChallengeCategory,
    ChallengeDifficulty,
    ChallengeFormat,
)
from app.services.challenge_service import ChallengeService


class TestChallengeServiceHelpers:
    def test_get_options_list_valid(self):
        """Парсинг JSON-списка вариантов ответов."""
        ch = Challenge(
            external_id="T01",
            title="Тест",
            category=ChallengeCategory.LOGIC,
            difficulty=ChallengeDifficulty.EASY,
            format=ChallengeFormat.MULTIPLE_CHOICE,
            answer_type=AnswerType.CHOICE,
            description="Описание",
            explanation="Объяснение",
            options=json.dumps(["Вариант А", "Вариант Б", "Вариант В"]),
        )
        ChallengeService(session=None)  # session not needed for pure method
        options = json.loads(ch.options)
        assert len(options) == 3
        assert options[0] == "Вариант А"

    def test_get_options_list_none(self):
        """Парсинг пустого списка вариантов."""
        ch = Challenge(
            external_id="T02",
            title="Тест без вариантов",
            category=ChallengeCategory.CREATIVE,
            difficulty=ChallengeDifficulty.HARD,
            format=ChallengeFormat.CO_CREATION,
            answer_type=AnswerType.TEXT,
            description="Описание",
            explanation="Объяснение",
            options=None,
        )
        assert ch.options is None
