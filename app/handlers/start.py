"""Хендлер /start — регистрация, онбординг и приветствие новичков."""

from __future__ import annotations

import contextlib
import logging
import re
from pathlib import Path

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, FSInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories import UserRepository
from app.keyboards.keyboards import (
    main_menu_keyboard,
    start_new_user_keyboard,
    start_registered_keyboard,
)
from app.services.xp_service import LEVEL_ICONS, LEVEL_NAMES, get_progress_bar

logger = logging.getLogger(__name__)
router = Router()

BANNER_PATH = Path(__file__).resolve().parent.parent / "assets" / "banner.png"
ALT_BANNER_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "фото"
    / "d4edb58b-642f-4765-b972-4fb0b2d41c0a.png"
)

MENU_BUTTONS = {
    "⚔️ AI Battle",
    "⚔️ Битва",
    "⚔️ Сразиться",
    "🧠 Ежедневный",
    "🧠 Ежедневный вызов",
    "🧠 Ежедневное",
    "🧠 Ежедневное задание",
    "🎯 Выбрать задание",
    "🎯 Выбрать тему",
    "🎯 Темы",
    "🎯 Задания",
    "🏆 Рейтинг",
    "🏆 Таблица лидеров",
    "🏆 Топ",
    "👤 Профиль",
    "📊 Статистика",
    "🎖️ Достижения",
    "❓ Как играть",
    "❓ Помощь",
    "❓ Справка",
    "❓ Правила",
    "⚡ Быстрая игра",
    "⚡ Быстрая битва",
    "⚡ Играть",
}


def get_banner_file() -> FSInputFile | None:
    """Возвращает FSInputFile баннера бота, если файл существует."""
    if BANNER_PATH.exists() and BANNER_PATH.is_file():
        return FSInputFile(str(BANNER_PATH))
    if ALT_BANNER_PATH.exists() and ALT_BANNER_PATH.is_file():
        return FSInputFile(str(ALT_BANNER_PATH))
    return None


class RegistrationStates(StatesGroup):
    waiting_for_name = State()


def _format_user_dashboard(user) -> str:
    """Формирует текст панели игрока."""
    icon = LEVEL_ICONS.get(user.level, "🌱")
    name = LEVEL_NAMES.get(user.level, "Новичок")
    bar = get_progress_bar(user.total_xp)

    return (
        f"⚡ С возвращением, <b>{user.display_name}</b>!\n\n"
        f"🏆 <b>Ранг:</b> {icon} {name} (Уровень {user.level})\n"
        f"⚡ <b>Опыт:</b> <code>{user.total_xp}</code> XP\n"
        f"🔥 <b>Серия побед:</b> {user.streak_days} дн.\n"
        f"📊 <b>Прогресс:</b> {bar}\n\n"
        "Выбери режим игры ниже 👇"
    )


def _format_welcome_newcomer(first_name: str) -> str:
    """Понятное и дружелюбное приветствие для новичка."""
    return (
        f"👋 Привет, <b>{first_name}</b>! Добро пожаловать в <b>AI Challenge</b>!\n\n"
        "🎮 <b>Что это за игра?</b>\n"
        "Это арена, где ты соревнуешься с искусственным интеллектом в сообразительности, логике и внимательности:\n\n"
        "• ⚔️ <b>AI Battle</b> — отвечай на каверзные вопросы быстрее нейросетей и находи скрытые ошибки ИИ\n"
        "• ⚡ <b>Быстрая игра</b> — мгновенные блиц-вызовы и проверка логики в один клик\n"
        "• 🏆 <b>Прокачка</b> — поднимайся от Новичка до Сверхразума и борись за топ игроков!\n\n"
        "Нажми кнопку ниже, чтобы начать 👇"
    )


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, state: FSMContext) -> None:
    """Обработчик команды /start."""
    await state.clear()
    if not message.from_user:
        return

    user_id = message.from_user.id
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)

    banner = get_banner_file()

    # 1. Зарегистрированный пользователь
    if user:
        text = _format_user_dashboard(user)
        keyboard = start_registered_keyboard()

        if banner:
            try:
                await message.answer_photo(
                    photo=banner,
                    caption=text,
                    reply_markup=keyboard,
                    parse_mode="HTML",
                )
                await message.answer(
                    "Главное меню доступно в кнопках ниже 👇", reply_markup=main_menu_keyboard()
                )
                return
            except Exception as e:
                logger.warning("Failed to send banner photo: %s", e)

        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        await message.answer(
            "Главное меню доступно в кнопках ниже 👇", reply_markup=main_menu_keyboard()
        )
        return

    # 2. Новый пользователь — даём понятный интерфейс в 1 клик
    first_name = message.from_user.first_name or "Игрок"
    text = _format_welcome_newcomer(first_name)
    keyboard = start_new_user_keyboard(suggested_name=first_name)

    if banner:
        try:
            await message.answer_photo(
                photo=banner,
                caption=text,
                reply_markup=keyboard,
                parse_mode="HTML",
            )
            await message.answer(
                "После старта меню появится на клавиатуре 📱", reply_markup=main_menu_keyboard()
            )
            return
        except Exception as e:
            logger.warning("Failed to send banner photo: %s", e)

    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await message.answer(
        "После старта меню появится на клавиатуре 📱", reply_markup=main_menu_keyboard()
    )


@router.callback_query(F.data == "fast_register")
async def on_fast_register(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    """Быстрая регистрация в 1 клик по имени Telegram."""
    with contextlib.suppress(Exception):
        await callback.answer()
    await state.clear()
    if not callback.from_user or not isinstance(callback.message, Message):
        return

    user_id = callback.from_user.id
    user_repo = UserRepository(session)
    first_name = (callback.from_user.first_name or "Игрок").strip()
    clean_name = re.sub(r'[<>&"\'\\]', "", first_name).strip() or "Игрок"

    user, _created = await user_repo.get_or_create(
        user_id=user_id,
        display_name=clean_name,
        username=callback.from_user.username,
        language_code="ru",
    )

    welcome_text = (
        f"🎉 <b>Добро пожаловать в игру, {clean_name}!</b>\n\n"
        "Твой профиль успешно создан:\n"
        "🌱 Ранг: <b>Новичок (Уровень 1)</b>\n"
        "⚡ Опыт: <b>0 XP</b>\n"
        "🔥 Серия активности: <b>0 дн.</b>\n\n"
        "С чего начнём? Попробуй <b>Быструю игру</b> или пройди <b>Ежедневное задание</b> 👇"
    )

    keyboard = start_registered_keyboard()
    try:
        if callback.message.photo:
            await callback.message.edit_caption(
                caption=welcome_text,
                reply_markup=keyboard,
                parse_mode="HTML",
            )
        else:
            await callback.message.edit_text(
                welcome_text,
                reply_markup=keyboard,
                parse_mode="HTML",
            )
    except Exception as e:
        logger.warning("Failed to edit message in fast_register: %s", e)
        await callback.message.answer(
            welcome_text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )

    await callback.message.answer(
        "📱 Главное меню активировано внизу экрана 👇",
        reply_markup=main_menu_keyboard(),
    )


@router.callback_query(F.data == "custom_register")
async def on_custom_register(callback: CallbackQuery, state: FSMContext) -> None:
    """Запрос кастомного никнейма."""
    with contextlib.suppress(Exception):
        await callback.answer()
    if not isinstance(callback.message, Message):
        return

    text = (
        "✏️ <b>Как к тебе обращаться в игре?</b>\n\n"
        "Напиши своё имя или игровой никнейм в ответном сообщении.\n"
        "<i>(До 32 символов, буквы и цифры)</i>"
    )
    try:
        if callback.message.photo:
            await callback.message.edit_caption(caption=text, parse_mode="HTML")
        else:
            await callback.message.edit_text(text, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, parse_mode="HTML")

    await state.set_state(RegistrationStates.waiting_for_name)


@router.callback_query(F.data == "start_challenge")
async def on_start_challenge_alias(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    """Алиас для старта игры."""
    with contextlib.suppress(Exception):
        await callback.answer()
    if not callback.from_user:
        return

    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(callback.from_user.id)
    if user:
        from app.handlers.challenges import on_quick_battle

        await on_quick_battle(callback, session, state)
    else:
        await on_fast_register(callback, session, state)


@router.message(RegistrationStates.waiting_for_name)
async def on_name_entered(message: Message, session: AsyncSession, state: FSMContext) -> None:
    """Обработка введённого кастомного имени."""
    if not message.from_user:
        return

    raw_name = (message.text or "").strip()

    if raw_name.startswith("/start"):
        await state.clear()
        await cmd_start(message, session, state)
        return

    user_repo = UserRepository(session)

    # Если вместо имени нажали кнопку меню
    if raw_name in MENU_BUTTONS or raw_name.startswith("/"):
        # Регистрируем пользователя по умолчанию и возвращаем в меню
        first_name = message.from_user.first_name or "Игрок"
        clean_name = re.sub(r'[<>&"\'\\]', "", first_name).strip() or "Игрок"
        await user_repo.get_or_create(
            user_id=message.from_user.id,
            display_name=clean_name,
            username=message.from_user.username,
            language_code="ru",
        )
        await state.clear()
        await message.answer(
            f"✅ Профиль создан с именем <b>{clean_name}</b>!",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML",
        )
        await cmd_start(message, session, state)
        return

    # Валидация имени
    clean_name = re.sub(r'[<>&"\'\\]', "", raw_name).strip()
    if not clean_name or len(clean_name) > 32:
        clean_name = message.from_user.first_name or "Игрок"

    user, _created = await user_repo.get_or_create(
        user_id=message.from_user.id,
        display_name=clean_name,
        username=message.from_user.username,
        language_code="ru",
    )

    await state.clear()

    welcome_text = (
        f"🎉 <b>Отлично, {clean_name}! Профиль готов!</b>\n\n"
        "🌱 Твой ранг: <b>Новичок (Уровень 1)</b>\n"
        "⚡ Опыт: <b>0 XP</b>\n\n"
        "Выбери первое испытание прямо сейчас 👇"
    )

    await message.answer(
        welcome_text,
        reply_markup=start_registered_keyboard(),
        parse_mode="HTML",
    )
    await message.answer(
        "📱 Главное меню активировано внизу экрана 👇",
        reply_markup=main_menu_keyboard(),
    )
    logger.info("User registered/updated: user_id=%s, name=%s", message.from_user.id, clean_name)
