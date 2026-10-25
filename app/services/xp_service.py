"""
XP и уровни — бизнес-логика расчёта прогресса.
Все расчёты выполняются только на сервере.
"""

from __future__ import annotations

# Пороги XP для каждого уровня
LEVEL_THRESHOLDS = {
    1: 0,  # Новичок
    2: 100,  # Исследователь
    3: 300,  # Промпт-инженер
    4: 700,  # AI-стратег
    5: 1500,  # Мастер челленджей
    6: 3000,  # AI Champion
}

LEVEL_NAMES = {
    1: "Новичок",
    2: "Исследователь",
    3: "Промпт-инженер",
    4: "AI-стратег",
    5: "Мастер челленджей",
    6: "AI Champion",
}

LEVEL_ICONS = {
    1: "🌱",
    2: "🔍",
    3: "✍️",
    4: "🧠",
    5: "⚔️",
    6: "👑",
}

MAX_LEVEL = 6


def get_level(total_xp: int) -> int:
    """Вычислить уровень по общему XP."""
    level = 1
    for lvl, threshold in sorted(LEVEL_THRESHOLDS.items(), reverse=True):
        if total_xp >= threshold:
            level = lvl
            break
    return min(level, MAX_LEVEL)


def get_xp_for_next_level(current_xp: int) -> tuple[int, int]:
    """
    Вернуть (XP до следующего уровня, порог следующего уровня).
    Если максимальный уровень, вернуть (0, current_xp).
    """
    current_level = get_level(current_xp)
    if current_level >= MAX_LEVEL:
        return 0, current_xp

    next_threshold = LEVEL_THRESHOLDS[current_level + 1]
    xp_needed = next_threshold - current_xp
    return max(0, xp_needed), next_threshold


def get_progress_bar(current_xp: int, bar_length: int = 10) -> str:
    """Символический прогресс-бар для Telegram."""
    level = get_level(current_xp)
    if level >= MAX_LEVEL:
        return "█" * bar_length + " MAX"

    current_threshold = LEVEL_THRESHOLDS[level]
    next_threshold = LEVEL_THRESHOLDS[level + 1]
    range_xp = next_threshold - current_threshold
    progress_xp = current_xp - current_threshold

    filled = int((progress_xp / range_xp) * bar_length)
    filled = max(0, min(bar_length, filled))
    empty = bar_length - filled

    return "█" * filled + "░" * empty


def calculate_xp_for_attempt(
    xp_base: int,
    xp_max: int,
    is_correct: bool,
    score_percent: float,
    is_first_attempt: bool,
    difficulty_multiplier: float = 1.0,
    xp_multiplier: float = 1.0,
) -> int:
    """
    Рассчитать XP за попытку.
    Все расчёты выполняются на сервере, не доверяем входным данным от пользователя.
    """
    if not is_first_attempt:
        return 0  # Повторные попытки не дают XP

    if not is_correct and score_percent < 30.0:
        return 0

    # Базовый расчёт
    score_ratio = score_percent / 100.0
    xp_range = xp_max - xp_base
    raw_xp = xp_base + int(xp_range * score_ratio)

    # Применяем множитель AI-оценки (ограничен)
    ai_mult = max(0.5, min(1.5, xp_multiplier))
    result = int(raw_xp * difficulty_multiplier * ai_mult)

    # Жёсткий потолок по xp_max
    return min(result, xp_max)


DIFFICULTY_MULTIPLIERS = {
    "easy": 1.0,
    "medium": 1.3,
    "hard": 1.7,
}
