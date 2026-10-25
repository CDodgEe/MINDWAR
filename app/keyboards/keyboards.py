"""Клавиатуры для AI Challenge Bot."""

from __future__ import annotations

from aiogram.types import (
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню бота (удобное и компактное)."""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="⚔️ AI Battle"),
        KeyboardButton(text="⚡ Быстрая игра"),
    )
    builder.row(
        KeyboardButton(text="🎯 Выбрать задание"),
        KeyboardButton(text="🏆 Рейтинг"),
    )
    builder.row(
        KeyboardButton(text="👤 Профиль"),
        KeyboardButton(text="❓ Как играть"),
    )
    return builder.as_markup(resize_keyboard=True, is_persistent=True)


def start_new_user_keyboard(suggested_name: str | None = None) -> InlineKeyboardMarkup:
    """Клавиатура для нового пользователя при старте."""
    builder = InlineKeyboardBuilder()
    name_label = f" (как {suggested_name[:14]})" if suggested_name else ""
    builder.button(text=f"🚀 Начать игру{name_label}", callback_data="fast_register")
    builder.button(text="✏️ Ввести другое имя", callback_data="custom_register")
    builder.button(text="❓ Как играть (Гайд за 30 сек)", callback_data="show_help")
    builder.adjust(1)
    return builder.as_markup()


def start_keyboard() -> InlineKeyboardMarkup:
    """Кнопка старта для обратной совместимости."""
    return start_new_user_keyboard()


def start_registered_keyboard() -> InlineKeyboardMarkup:
    """Интерактивное меню для зарегистрированного игрока."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⚡ Быстрая игра (Блиц-вызов)", callback_data="quick_battle")
    builder.button(text="🎯 Выбрать категорию", callback_data="choose_category")
    builder.button(text="🏆 Рейтинг", callback_data="show_leaderboard")
    builder.button(text="👤 Мой профиль", callback_data="show_profile")
    builder.button(text="❓ Как играть", callback_data="show_help")
    builder.adjust(1, 2, 2)
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
    builder.button(text="🎲 Любая категория", callback_data="cat_random")
    builder.adjust(2, 2, 2, 1)
    return builder.as_markup()


def options_keyboard(
    options: list[str],
    challenge_id: int,
    prefix: str = "answer",
) -> InlineKeyboardMarkup:
    """
    Варианты ответов для задания с выбором.
    Поддерживает кастомный префикс (например daily_ans для ежедневного задания).
    """
    builder = InlineKeyboardBuilder()
    letters = ["А", "Б", "В", "Г", "Д"]
    for i, opt in enumerate(options):
        letter = letters[i] if i < len(letters) else str(i + 1)
        clean_opt = opt.strip()
        btn_text = f"{letter}) {clean_opt}"
        if len(btn_text) > 42:
            btn_text = btn_text[:39] + "..."
        builder.button(
            text=btn_text,
            callback_data=f"{prefix}_{challenge_id}_{i}",
        )
    builder.adjust(1)
    return builder.as_markup()


def battle_format_keyboard() -> InlineKeyboardMarkup:
    """Выбор формата битвы с понятными описаниями."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⚡ Быстрая игра (Случайный вызов)", callback_data="quick_battle")
    builder.button(text="⚔️ Human First (Ответь быстрее ИИ)", callback_data="fmt_human_first")
    builder.button(text="🕵️ AI Detective (Найди ошибку ИИ)", callback_data="fmt_ai_detective")
    builder.button(text="🤝 Co-Creation (Улучши ответ ИИ)", callback_data="fmt_co_creation")
    builder.button(text="🎯 Выбрать по темам", callback_data="choose_category")
    builder.adjust(1)
    return builder.as_markup()


def after_challenge_keyboard(
    challenge_id: int | None = None,  # noqa: ARG001
    is_daily: bool = False,  # noqa: ARG001
) -> InlineKeyboardMarkup:
    """Действия после прохождения задания."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⚔️ Следующий вызов", callback_data="next_challenge")
    builder.button(text="🎯 Выбрать тему", callback_data="choose_category")
    builder.button(text="🏆 Рейтинг", callback_data="show_leaderboard")
    builder.button(text="👤 Мой профиль", callback_data="show_profile")
    builder.adjust(2, 2)
    return builder.as_markup()


def profile_keyboard() -> InlineKeyboardMarkup:
    """Профиль — действия."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⚔️ В бой!", callback_data="quick_battle")
    builder.button(text="📊 Статистика", callback_data="show_stats")
    builder.button(text="🎖️ Достижения", callback_data="show_achievements")
    builder.button(text="⚙️ Настройки", callback_data="settings")
    builder.button(text="🗑️ Удалить аккаунт", callback_data="delete_account_confirm")
    builder.adjust(1, 2, 1, 1)
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
    builder.button(text="⬅️ Назад в профиль", callback_data="show_profile")
    builder.adjust(1)
    return builder.as_markup()


def back_to_profile_keyboard() -> InlineKeyboardMarkup:
    """Возврат в профиль."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад в профиль", callback_data="show_profile")
    return builder.as_markup()


def leaderboard_keyboard() -> InlineKeyboardMarkup:
    """Кнопки под таблицей лидеров."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⚡ Быстрая игра", callback_data="quick_battle")
    builder.button(text="👤 Мой профиль", callback_data="show_profile")
    builder.adjust(2)
    return builder.as_markup()


def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()
