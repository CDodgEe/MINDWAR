"""Тесты для ежедневных заданий и онбординга."""

import pytest

from app.database.models import AnswerType
from app.database.repositories import ChallengeRepository
from app.database.session import AsyncSessionFactory
from app.keyboards.keyboards import (
    main_menu_keyboard,
    options_keyboard,
    start_new_user_keyboard,
    start_registered_keyboard,
)
from app.services.daily_service import DailyChallengeService


@pytest.mark.asyncio
async def test_daily_challenge_always_has_choice_options():
    """Проверяет, что ежедневное задание всегда содержит варианты выбора."""
    async with AsyncSessionFactory() as session:
        daily_service = DailyChallengeService(session)
        challenge, date_str = await daily_service.get_or_assign_daily()

        assert challenge is not None
        assert challenge.answer_type == AnswerType.CHOICE
        assert challenge.options is not None

        repo = ChallengeRepository(session)
        eligible = await repo.get_daily_eligible()
        assert len(eligible) > 0
        for ch in eligible:
            assert ch.answer_type == AnswerType.CHOICE
            assert ch.options is not None


def test_options_keyboard_generation():
    """Проверяет генерацию клавиатуры вариантов ответа."""
    options = ["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4"]
    kb = options_keyboard(options, challenge_id=10, prefix="daily_ans")
    assert len(kb.inline_keyboard) == 4
    for i, row in enumerate(kb.inline_keyboard):
        button = row[0]
        assert button.callback_data == f"daily_ans_10_{i}"


def test_onboarding_keyboards():
    """Проверяет клавиатуры онбординга."""
    new_kb = start_new_user_keyboard("Тест")
    assert len(new_kb.inline_keyboard) >= 2

    reg_kb = start_registered_keyboard()
    assert len(reg_kb.inline_keyboard) >= 3

    menu_kb = main_menu_keyboard()
    assert len(menu_kb.keyboard) == 3
