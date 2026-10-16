"""Хендлер /start — регистрация и онбординг."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories import UserRepository
from app.keyboards.keyboards import (
    language_keyboard,
    main_menu_keyboard,
    start_keyboard,
)
from app.services.xp_service import LEVEL_ICONS, LEVEL_NAMES, get_progress_bar

logger = logging.getLogger(__name__)
router = Router()

WELCOME_TEXT = """⚡ <b>AI CHALLENGE</b>

ИИ уже умеет писать, анализировать и создавать.

Но сможет ли он решить задачу лучше тебя?

🧠 Проверь логику.
⚔️ Вступи в AI Battle.
🔎 Найди ошибки искусственного интеллекта.
🏆 Прокачай свой уровень.

<i>«Think smarter. Create better. Challenge AI.»</i>

Готов проверить себя?"""


class RegistrationStates(StatesGroup):
    waiting_for_name = State()


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, state: FSMContext) -> None:
    """Обработчик команды /start."""
    user_id = message.from_user.id
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)

    if user:
        # Уже зарегистрирован
        await message.answer(
            f"⚡ С возвращением, <b>{user.display_name}</b>!\n\n"
            f"Уровень: {LEVEL_ICONS.get(user.level, '🌱')} {LEVEL_NAMES.get(user.level, 'Новичок')}\n"
            f"XP: <code>{user.total_xp}</code>\n"
            f"Прогресс: {get_progress_bar(user.total_xp)}",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML",
        )
        return

    # Новый пользователь
    await state.clear()
    await message.answer(
        WELCOME_TEXT,
        reply_markup=start_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "start_challenge")
async def on_start_challenge(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало регистрации."""
    await callback.message.edit_text(
        "🌐 <b>Выбери язык интерфейса:</b>",
        reply_markup=language_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "lang_ru")
async def on_language_ru(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбор русского языка."""
    await state.update_data(language="ru")
    await callback.message.edit_text(
        "👤 <b>Как тебя зовут?</b>\n\n"
        "Введи своё имя или придумай игровой псевдоним.\n"
        "<i>(Максимум 32 символа, только буквы и цифры)</i>",
        parse_mode="HTML",
    )
    await state.set_state(RegistrationStates.waiting_for_name)
    await callback.answer()


@router.callback_query(F.data == "lang_kz_soon")
async def on_language_kz_soon(callback: CallbackQuery) -> None:
    await callback.answer("🇰🇿 Қазақша нұсқасы жақында қосылады!", show_alert=True)


@router.message(RegistrationStates.waiting_for_name)
async def on_name_entered(message: Message, session: AsyncSession, state: FSMContext) -> None:
    """Обработка введённого имени."""
    raw_name = message.text.strip() if message.text else ""

    # Валидация имени
    if not raw_name:
        await message.answer("❌ Имя не может быть пустым. Попробуй ещё раз:")
        return

    if len(raw_name) > 32:
        await message.answer("❌ Имя слишком длинное (максимум 32 символа):")
        return

    # Фильтруем опасные символы
    import re
    clean_name = re.sub(r'[<>&"\'\\]', '', raw_name)
    if not clean_name:
        await message.answer("❌ Некорректное имя. Используй буквы и цифры:")
        return

    data = await state.get_data()
    language = data.get("language", "ru")

    # Регистрируем пользователя
    user_repo = UserRepository(session)
    user, created = await user_repo.get_or_create(
        user_id=message.from_user.id,
        display_name=clean_name,
        username=message.from_user.username,
        language_code=language,
    )

    await state.clear()

    # Показываем карточку игрока
    await message.answer(
        f"🎮 <b>Добро пожаловать, {clean_name}!</b>\n\n"
        f"┌─────────────────────┐\n"
        f"│  🌱 Уровень 1 — Новичок\n"
        f"│  ⚡ XP: 0\n"
        f"│  📊 Прогресс: {'░' * 10}\n"
        f"│  🏆 Победы: 0\n"
        f"└─────────────────────┘\n\n"
        f"Твой путь только начинается!\n"
        f"Выбери первый вызов 👇",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML",
    )

    logger.info("New user registered: user_id=%s, name=%s", message.from_user.id, clean_name)
