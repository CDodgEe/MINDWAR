"""Хендлер проведения челленджей — AI Battle."""

from __future__ import annotations

import contextlib
import html
import logging
import random
import time

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import AnswerType, ChallengeCategory, ChallengeFormat
from app.database.repositories import UserRepository
from app.keyboards.keyboards import (
    after_challenge_keyboard,
    battle_format_keyboard,
    category_keyboard,
    main_menu_keyboard,
    options_keyboard,
)
from app.services.challenge_service import ChallengeService
from app.services.xp_service import LEVEL_ICONS, LEVEL_NAMES

logger = logging.getLogger(__name__)
router = Router()


def escape_html(text: str | None) -> str:
    """Безопасное экранирование спецсимволов HTML (&, <, >)."""
    if not text:
        return ""
    return html.escape(str(text), quote=False)


async def _safe_edit_or_answer(
    event: Message | CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    """Надёжная отправка сообщения с fallback на чистый текст при ошибках парсинга HTML."""
    if isinstance(event, CallbackQuery) and isinstance(event.message, Message):
        try:
            await event.message.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")
        except Exception as e:
            logger.warning("edit_text with HTML failed (%s), retrying without parse_mode", e)
            await event.message.edit_text(text, reply_markup=reply_markup, parse_mode=None)
    elif isinstance(event, Message):
        try:
            await event.answer(text, reply_markup=reply_markup, parse_mode="HTML")
        except Exception as e:
            logger.warning("answer with HTML failed (%s), retrying without parse_mode", e)
            await event.answer(text, reply_markup=reply_markup, parse_mode=None)

CATEGORY_MAP = {
    "cat_logic": ChallengeCategory.LOGIC,
    "cat_prompt": ChallengeCategory.PROMPT,
    "cat_detective": ChallengeCategory.DETECTIVE,
    "cat_creative": ChallengeCategory.CREATIVE,
    "cat_cyber": ChallengeCategory.CYBER,
    "cat_real_life": ChallengeCategory.REAL_LIFE,
}

CATEGORY_NAMES = {
    ChallengeCategory.LOGIC: "🧩 Логика",
    ChallengeCategory.PROMPT: "✍️ Промпты",
    ChallengeCategory.DETECTIVE: "🕵️ AI Детектив",
    ChallengeCategory.CREATIVE: "🎨 Творчество",
    ChallengeCategory.CYBER: "🛡️ Кибербезопасность",
    ChallengeCategory.REAL_LIFE: "🌍 Реальная жизнь",
}

DIFFICULTY_DISPLAY = {
    "easy": "🟢 Лёгкий",
    "medium": "🟡 Средний",
    "hard": "🔴 Сложный",
}

FORMAT_DISPLAY = {
    ChallengeFormat.HUMAN_FIRST: "⚔️ Human First (Ответь быстрее ИИ)",
    ChallengeFormat.AI_DETECTIVE: "🕵️ AI Detective (Найди ошибку ИИ)",
    ChallengeFormat.CO_CREATION: "🤝 Co-Creation (Улучши ответ ИИ)",
    ChallengeFormat.MULTIPLE_CHOICE: "📝 Выбор ответа",
}


class ChallengeStates(StatesGroup):
    choosing_category = State()
    choosing_format = State()
    waiting_for_answer = State()
    waiting_for_text_answer = State()


async def _require_registration(message_or_cb: Message | CallbackQuery, session: AsyncSession) -> bool:
    """Проверить регистрацию пользователя или зарегистрировать автоматически."""
    if not message_or_cb.from_user:
        return False

    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(message_or_cb.from_user.id)
    if not user:
        display_name = message_or_cb.from_user.first_name or f"Игрок_{message_or_cb.from_user.id % 10000}"
        await user_repo.create(
            user_id=message_or_cb.from_user.id,
            display_name=display_name,
            username=message_or_cb.from_user.username,
        )
    return True


async def _show_challenge(
    event: Message | CallbackQuery,
    challenge,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Отображение карточки задания игроку."""
    await state.update_data(challenge_id=challenge.id, start_time=time.time())

    cat_name = CATEGORY_NAMES.get(challenge.category, "🎯 Задание")
    diff_name = DIFFICULTY_DISPLAY.get(challenge.difficulty.value, "🟢 Лёгкий")
    fmt_name = FORMAT_DISPLAY.get(challenge.format, "⚔️ AI Battle")

    header = (
        f"{cat_name} | {diff_name}\n"
        f"🎮 Режим: {fmt_name}\n"
        f"⚡ Награда: до +{challenge.xp_max} XP\n"
        "───────────────────\n\n"
    )

    ai_prefix = ""
    if challenge.format == ChallengeFormat.AI_DETECTIVE and challenge.ai_response:
        ai_prefix = (
            f"🤖 <b>Ответ нейросети:</b>\n"
            f"<i>«{escape_html(challenge.ai_response)}»</i>\n\n"
            f"🔍 <b>Где ошибка в ответе нейросети?</b>\n\n"
        )
    elif challenge.format == ChallengeFormat.CO_CREATION and challenge.ai_response:
        ai_prefix = (
            f"🤖 <b>Черновик ответа нейросети:</b>\n"
            f"<i>«{escape_html(challenge.ai_response)}»</i>\n\n"
            f"🤝 <b>Как улучшить этот ответ?</b>\n\n"
        )

    challenge_text = header + ai_prefix + escape_html(challenge.description)

    service = ChallengeService(session)
    if challenge.answer_type == AnswerType.CHOICE:
        options = await service.get_options_list(challenge)
        if options:
            letters = ["А", "Б", "В", "Г", "Д"]
            options_text = "\n".join(
                f"<b>{letters[i]})</b> {escape_html(opt)}" for i, opt in enumerate(options)
            )
            full_text = f"{challenge_text}\n\n<b>Варианты:</b>\n{options_text}"
            keyboard = options_keyboard(options, challenge.id, prefix="answer")

            await state.set_state(ChallengeStates.waiting_for_answer)
            await _safe_edit_or_answer(event, full_text, reply_markup=keyboard)
            return

    # Текстовый ввод
    full_text = challenge_text + "\n\n✍️ <b>Напиши свой ответ в сообщении ниже:</b>"
    await state.set_state(ChallengeStates.waiting_for_text_answer)
    await _safe_edit_or_answer(event, full_text)


@router.message(F.text.in_(["⚔️ AI Battle", "⚔️ Битва", "⚔️ Сразиться"]))
@router.message(Command("challenge"))
@router.message(Command("battle"))
async def cmd_challenge(message: Message, session: AsyncSession, state: FSMContext) -> None:
    """Запуск меню AI Battle."""
    if not message.from_user:
        return
    await _require_registration(message, session)
    await state.clear()
    await message.answer(
        "⚔️ <b>AI BATTLE — АРЕНА БИТВЫ С ИИ</b>\n\n"
        "Выбери режим битвы или нажми <b>Быстрая игра</b> для мгновенного старта:\n\n"
        "⚡ <b>Быстрая игра</b> — случайная интересная задача прямо сейчас\n"
        "🔹 <b>Human First</b> — ты отвечаешь первым, затем сравниваешь с ИИ\n"
        "🔹 <b>AI Detective</b> — находишь скрытую ошибку в ответе нейросети\n"
        "🔹 <b>Co-Creation</b> — улучшаешь и дополняешь шаблонный ответ ИИ",
        reply_markup=battle_format_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(ChallengeStates.choosing_format)


@router.callback_query(F.data == "quick_battle")
@router.message(F.text.in_(["⚡ Быстрая игра", "⚡ Быстрая битва", "⚡ Играть"]))
async def on_quick_battle(event: Message | CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    """Быстрый старт игры в один клик без лишних меню."""
    if not event.from_user:
        return

    if isinstance(event, CallbackQuery):
        with contextlib.suppress(Exception):
            await event.answer()

    await _require_registration(event, session)
    await state.clear()

    service = ChallengeService(session)
    challenge = await service.get_random_challenge()

    if not challenge:
        msg = "😔 Заданий пока нет. Попробуй позже."
        if isinstance(event, CallbackQuery) and isinstance(event.message, Message):
            await event.message.edit_text(msg, reply_markup=after_challenge_keyboard())
        elif isinstance(event, Message):
            await event.answer(msg, reply_markup=main_menu_keyboard())
        return

    await _show_challenge(event, challenge, session, state)


@router.callback_query(ChallengeStates.choosing_format, F.data.startswith("fmt_"))
async def on_format_selected(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбор формата битвы."""
    with contextlib.suppress(Exception):
        await callback.answer()

    if not callback.data or not isinstance(callback.message, Message):
        return

    fmt_key = callback.data

    if fmt_key == "fmt_random":
        fmt_key = random.choice(["fmt_human_first", "fmt_ai_detective", "fmt_co_creation"])  # noqa: S311

    format_map = {
        "fmt_human_first": ChallengeFormat.HUMAN_FIRST,
        "fmt_ai_detective": ChallengeFormat.AI_DETECTIVE,
        "fmt_co_creation": ChallengeFormat.CO_CREATION,
    }
    selected_format = format_map.get(fmt_key, ChallengeFormat.HUMAN_FIRST)

    await state.update_data(selected_format=selected_format.value)
    await callback.message.edit_text(
        "🎯 <b>Выбери тему задания:</b>",
        reply_markup=category_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(ChallengeStates.choosing_category)


@router.message(F.text.in_(["🎯 Выбрать задание", "🎯 Выбрать тему", "🎯 Темы", "🎯 Задания"]))
async def cmd_choose_category(
    message: Message, session: AsyncSession, state: FSMContext
) -> None:
    """Выбор темы задания."""
    if not message.from_user:
        return

    await _require_registration(message, session)
    await state.clear()
    await state.update_data(selected_format=None)
    await message.answer(
        "🎯 <b>Выбери категорию заданий:</b>\n\n"
        "От логики и детективных загадок до кибербезопасности и промпт-инжиниринга 👇",
        reply_markup=category_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(ChallengeStates.choosing_category)


@router.callback_query(
    ChallengeStates.choosing_category,
    F.data.in_(list(CATEGORY_MAP.keys()) + ["cat_random"]),
)
async def on_category_selected(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    """Выбор категории и загрузка задания."""
    with contextlib.suppress(Exception):
        await callback.answer()

    if not callback.data or not isinstance(callback.message, Message):
        return

    data = await state.get_data()
    category = CATEGORY_MAP.get(callback.data)
    selected_format_str = data.get("selected_format")
    selected_format = None
    if selected_format_str:
        with contextlib.suppress(ValueError):
            selected_format = ChallengeFormat(selected_format_str)

    service = ChallengeService(session)
    challenge = await service.get_random_challenge(category=category, challenge_format=selected_format)

    if not challenge:
        challenge = await service.get_random_challenge(category=category)

    if not challenge:
        await callback.message.edit_text(
            "😔 В этой категории пока нет доступных заданий. Попробуй другую!",
            reply_markup=category_keyboard(),
        )
        return

    await _show_challenge(callback, challenge, session, state)


@router.callback_query(F.data.startswith("answer_"))
async def on_choice_answer(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    """Обработка ответа с выбором варианта (с мгновенной реакцией)."""
    with contextlib.suppress(Exception):
        await callback.answer()

    if not callback.from_user or not callback.data or not isinstance(callback.message, Message):
        return

    parts = callback.data.split("_")
    if len(parts) < 3:
        return

    try:
        challenge_id = int(parts[-2])
        selected_index = int(parts[-1])
    except ValueError:
        return

    state_data = await state.get_data()
    start_time = state_data.get("start_time", time.time())
    time_spent = int(time.time() - start_time)

    service = ChallengeService(session)
    challenge = await service.get_challenge(challenge_id)
    if not challenge:
        await callback.message.edit_text(
            "⚠️ Задание не найдено или завершено.",
            reply_markup=after_challenge_keyboard(),
        )
        await state.clear()
        return

    result = await service.submit_choice_answer(
        user_id=callback.from_user.id,
        challenge=challenge,
        selected_index=selected_index,
        time_spent=time_spent,
    )

    await state.clear()
    await _send_result(callback.message, result, challenge, edit=True)


@router.message(ChallengeStates.waiting_for_text_answer)
async def on_text_answer(
    message: Message, session: AsyncSession, state: FSMContext
) -> None:
    """Обработка текстового ответа."""
    if not message.from_user or not message.text:
        await message.answer("Пожалуйста, отправь ответ текстом.")
        return

    state_data = await state.get_data()
    challenge_id = state_data.get("challenge_id")
    start_time = state_data.get("start_time", time.time())
    time_spent = int(time.time() - start_time)

    service = ChallengeService(session)
    challenge = None
    if challenge_id:
        challenge = await service.get_challenge(challenge_id)

    if not challenge:
        await message.answer("Задание не найдено. Начни новый вызов:", reply_markup=main_menu_keyboard())
        await state.clear()
        return

    processing_msg = await message.answer("⏳ Анализирую твой ответ...")

    try:
        result = await service.submit_text_answer(
            user_id=message.from_user.id,
            challenge=challenge,
            user_answer=message.text,
            time_spent=time_spent,
        )
        await state.clear()
        with contextlib.suppress(Exception):
            await processing_msg.delete()
        await _send_result(message, result, challenge, edit=False)
    except Exception as e:
        logger.error(f"Error evaluating text answer: {e}", exc_info=True)
        await state.clear()
        with contextlib.suppress(Exception):
            await processing_msg.delete()
        await message.answer(
            "⚠️ Произошла ошибка при оценке ответа. Попробуй ещё раз или выбери другое задание.",
            reply_markup=after_challenge_keyboard(challenge.id),
        )


async def _send_result(
    msg: Message,
    result: dict,
    challenge,
    edit: bool = False,
) -> None:
    """Отправить результат прохождения задания."""
    is_correct = result.get("is_correct", False)
    xp_earned = result.get("xp_earned", 0)
    score_percent = result.get("score_percent", 0)
    is_first = result.get("is_first_attempt", True)
    level_up = result.get("level_up", False)
    new_level = result.get("new_level")
    new_achievements = result.get("new_achievements", [])
    explanation = result.get("explanation", "")
    feedback = result.get("feedback", "")

    if is_correct:
        status_icon = "🎉"
        status_text = "ВЕРНО! ОТЛИЧНО!" if score_percent >= 80 else "ОТВЕТ ПРИНЯТ!"
    else:
        status_icon = "❌"
        status_text = "НЕВЕРНО"

    xp_text = ""
    if xp_earned > 0 and is_first:
        xp_text = f"\n⚡ <b>Получено опыта:</b> +{xp_earned} XP"
    elif not is_first:
        xp_text = "\n💡 <i>(XP за повторное прохождение не начисляется)</i>"

    result_text = f"{status_icon} <b>{status_text}</b>{xp_text}\n\n"

    if feedback and feedback != explanation:
        result_text += f"💬 <b>Комментарий:</b> {escape_html(feedback)}\n\n"

    if explanation:
        result_text += f"📖 <b>Разбор:</b>\n{escape_html(explanation)}"

    if level_up and new_level:
        level_icon = LEVEL_ICONS.get(new_level, "🌟")
        level_name = LEVEL_NAMES.get(new_level, "")
        result_text += f"\n\n🚀 <b>ПОВЫШЕНИЕ РАНГА!</b>\n{level_icon} <b>{level_name}</b> (Уровень {new_level})"

    if new_achievements:
        result_text += "\n\n🏅 <b>Новые достижения:</b>"
        for ach in new_achievements:
            result_text += f"\n{ach.icon} <b>{ach.name}</b> (+{ach.xp_reward} XP)"

    keyboard = after_challenge_keyboard(challenge.id)

    if edit:
        try:
            await msg.edit_text(result_text, reply_markup=keyboard, parse_mode="HTML")
        except Exception as e:
            logger.warning("edit_text with HTML failed (%s), retrying without parse_mode", e)
            await msg.edit_text(result_text, reply_markup=keyboard, parse_mode=None)
    else:
        try:
            await msg.answer(result_text, reply_markup=keyboard, parse_mode="HTML")
        except Exception as e:
            logger.warning("answer with HTML failed (%s), retrying without parse_mode", e)
            await msg.answer(result_text, reply_markup=keyboard, parse_mode=None)


@router.callback_query(F.data == "next_challenge")
async def on_next_challenge(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    """Следующий случайный вызов."""
    with contextlib.suppress(Exception):
        await callback.answer()
    if not isinstance(callback.message, Message):
        return

    await state.clear()
    service = ChallengeService(session)
    challenge = await service.get_random_challenge()

    if not challenge:
        await callback.message.edit_text("Заданий пока нет.", reply_markup=after_challenge_keyboard())
        return

    await _show_challenge(callback, challenge, session, state)


@router.callback_query(F.data == "choose_category")
async def on_choose_category_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбор категории через callback."""
    with contextlib.suppress(Exception):
        await callback.answer()
    if not isinstance(callback.message, Message):
        return

    await state.clear()
    await state.update_data(selected_format=None)
    await callback.message.edit_text(
        "🎯 <b>Выбери категорию заданий:</b>",
        reply_markup=category_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(ChallengeStates.choosing_category)
