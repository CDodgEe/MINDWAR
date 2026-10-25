"""
Тесты бизнес-логики начисления опыта (XP), рангов и прогресса.
"""

from __future__ import annotations

from app.services.xp_service import (
    DIFFICULTY_MULTIPLIERS,
    LEVEL_NAMES,
    calculate_xp_for_attempt,
    get_level,
    get_progress_bar,
    get_xp_for_next_level,
)


class TestXPService:
    def test_level_calculation(self):
        """Проверка порогов уровней."""
        assert get_level(0) == 1
        assert get_level(99) == 1
        assert get_level(100) == 2
        assert get_level(299) == 2
        assert get_level(300) == 3
        assert get_level(699) == 3
        assert get_level(700) == 4
        assert get_level(1499) == 4
        assert get_level(1500) == 5
        assert get_level(3000) == 6

    def test_level_names(self):
        """Проверка названий рангов."""
        assert LEVEL_NAMES[1] == "Новичок"
        assert LEVEL_NAMES[2] == "Исследователь"
        assert LEVEL_NAMES[3] == "Промпт-инженер"
        assert LEVEL_NAMES[4] == "AI-стратег"
        assert LEVEL_NAMES[5] == "Мастер челленджей"
        assert LEVEL_NAMES[6] == "AI Champion"

    def test_calculate_xp_first_attempt_correct(self):
        """Проверка начисления XP за первую правильную попытку."""
        xp = calculate_xp_for_attempt(
            xp_base=10,
            xp_max=30,
            is_correct=True,
            score_percent=100.0,
            is_first_attempt=True,
            difficulty_multiplier=DIFFICULTY_MULTIPLIERS["easy"],
            xp_multiplier=1.0,
        )
        assert xp >= 10
        assert xp <= 30

    def test_calculate_xp_replay_returns_zero(self):
        """Повторные попытки не дают XP (предотвращение фарма)."""
        xp_repeat = calculate_xp_for_attempt(
            xp_base=10,
            xp_max=30,
            is_correct=True,
            score_percent=100.0,
            is_first_attempt=False,
            difficulty_multiplier=DIFFICULTY_MULTIPLIERS["hard"],
            xp_multiplier=1.0,
        )
        assert xp_repeat == 0

    def test_calculate_xp_failed_attempt(self):
        """Неправильный ответ с низким баллом не даёт XP."""
        xp = calculate_xp_for_attempt(
            xp_base=10,
            xp_max=30,
            is_correct=False,
            score_percent=10.0,
            is_first_attempt=True,
        )
        assert xp == 0

    def test_calculate_xp_for_next_level(self):
        """Проверка оставшегося опыта до следующего уровня."""
        needed, threshold = get_xp_for_next_level(current_xp=50)
        assert needed == 50
        assert threshold == 100

    def test_progress_bar_format(self):
        """Проверка генерации визуального прогресс-бара."""
        bar_0 = get_progress_bar(0)
        bar_mid = get_progress_bar(50)
        assert isinstance(bar_0, str)
        assert isinstance(bar_mid, str)
        assert len(bar_0) > 0
