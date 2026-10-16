"""Клавиатуры для AI Challenge Bot."""

from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from app.database.models import ChallengeCategory


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню."""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="⚔️ AI Battle"),
        KeyboardButton(text="🧠 Ежедневный"),
    )
    builder.row(
        KeyboardButton(text="🎯 Выбрать задание"),
        KeyboardButton(text="🏆 Рейтинг"),
    )
    builder.row(
        KeyboardButton(text="👤 Профиль"),
        KeyboardButton(text="📊 Статистика"),
    )
    builder.row(
        KeyboardButton(text="🎖️ Достижения"),
        KeyboardButton(text="❓ Как играть"),
    )
    return builder.as_markup(resize_keyboard=True, is_persistent=True)


def start_keyboard() -> InlineKeyboardMarkup:
    """Кнопка старта."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🚀 Начать челлендж", callback_data="start_challenge")
    return builder.as_markup()


def language_keyboard() -> InlineKeyboardMarkup:
    """Выбор языка."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🇷🇺 Русский", callback_data="lang_ru")
    builder.button(text="🇰🇿 Қазақша (скоро)", callback_data="lang_kz_soon")
    builder.adjust(2)
    return builder.as_markup()


def category_keyboard() -> InlineKeyboardMarkup:
    """Выбор категории задания."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🧩 Логика", callback_data="cat_logic")
    builder.button(text="✍️ Промпты", callback_data="cat_prompt")
    builder.button(text="🕵️ AI Детектив", callback_data="cat_detective")
    builder.button(text="🎨 Творчество", callback_data="cat_creative")
    builder.button(text="🛡️ Кибербезопасность", callback_data="cat_cyber")
    builder.button(text="🌍 Реальная жизнь", callback_data="cat_real_life")
    builder.button(text="🎲 Случайное", callback_data="cat_random")
    builder.adjust(2, 2, 2, 1)
    return builder.as_markup()


def options_keyboard(options: list[str], challenge_id: int) -> InlineKeyboardMarkup:
    """Варианты ответов для задания с выбором."""
    builder = InlineKeyboardBuilder()
    letters = ["А", "Б", "В", "Г", "Д"]
    for i, opt in enumerate(options):
        letter = letters[i] if i < len(letters) else str(i)
        builder.button(
            text=f"{letter}) {opt[:40]}{'...' if len(opt) > 40 else ''}",
            callback_data=f"answer_{challenge_id}_{i}",
        )
    builder.adjust(1)
    return builder.as_markup()


def battle_format_keyboard() -> InlineKeyboardMarkup:
    """Выбор формата битвы."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⚔️ Human First — ответь первым", callback_data="fmt_human_first")
    builder.button(text="🕵️ AI Detective — найди ошибку", callback_data="fmt_ai_detective")
    builder.button(text="🤝 Co-Creation — улучши ответ AI", callback_data="fmt_co_creation")
    builder.button(text="🎲 Случайный формат", callback_data="fmt_random")
    builder.adjust(1)
    return builder.as_markup()


def after_challenge_keyboard(challenge_id: int | None = None) -> InlineKeyboardMarkup:
    """Действия после прохождения задания."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⚔️ Следующий вызов", callback_data="next_challenge")
    builder.button(text="🎯 Выбрать категорию", callback_data="choose_category")
    builder.button(text="🏆 Рейтинг", callback_data="show_leaderboard")
    builder.button(text="👤 Мой профиль", callback_data="show_profile")
    builder.adjust(2, 2)
    return builder.as_markup()


def profile_keyboard() -> InlineKeyboardMarkup:
    """Профиль — дополнительные действия."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Статистика", callback_data="show_stats")
    builder.button(text="🎖️ Достижения", callback_data="show_achievements")
    builder.button(text="⚙️ Настройки", callback_data="settings")
    builder.button(text="🗑️ Удалить аккаунт", callback_data="delete_account_confirm")
    builder.adjust(2, 1, 1)
    return builder.as_markup()


def confirm_keyboard(action: str) -> InlineKeyboardMarkup:
    """Подтверждение действия."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, подтвердить", callback_data=f"confirm_{action}")
    builder.button(text="❌ Отмена", callback_data="cancel_action")
    builder.adjust(2)
    return builder.as_markup()


def settings_keyboard(notifications_enabled: bool) -> InlineKeyboardMarkup:
    """Настройки уведомлений."""
    notif_text = "🔔 Уведомления: ВКЛ" if notifications_enabled else "🔕 Уведомления: ВЫКЛ"
    builder = InlineKeyboardBuilder()
    builder.button(text=notif_text, callback_data="toggle_notifications")
    builder.button(text="🔒 Скрыть из рейтинга", callback_data="toggle_leaderboard")
    builder.button(text="⬅️ Назад", callback_data="show_profile")
    builder.adjust(1)
    return builder.as_markup()


def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()
