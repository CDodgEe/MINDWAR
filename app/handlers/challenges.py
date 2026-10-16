"""Хендлер проведения челленджей — AI Battle."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
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
    ChallengeFormat.HUMAN_FIRST: "⚔️ Human First",
    ChallengeFormat.AI_DETECTIVE: "🕵️ AI Detective",
    ChallengeFormat.CO_CREATION: "🤝 Co-Creation",
    ChallengeFormat.MULTIPLE_CHOICE: "📝 Выбор ответа",
}


class ChallengeStates(StatesGroup):
    choosing_category = State()
    choosing_format = State()
    waiting_for_answer = State()
    waiting_for_text_answer = State()


async def _require_registration(message: Message, session: AsyncSession) -> bool:
    """Проверить регистрацию пользователя."""
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(message.from_user.id)
    if not user:
        await message.answer(
            "👋 Сначала зарегистрируйся — используй /start",
            reply_markup=main_menu_keyboard(),
        )
        return False
    return True


@router.message(F.text == "⚔️ AI Battle")
@router.message(Command("challenge"))
async def cmd_challenge(message: Message, session: AsyncSession, state: FSMContext) -> None:
    """Запуск AI Battle."""
    if not await _require_registration(message, session):
        return

    await state.clear()
    await message.answer(
        "⚔️ <b>AI BATTLE</b>\n\n"
        "Выбери формат битвы с искусственным интеллектом:\n\n"
        "🔹 <b>Human First</b> — ты отвечаешь первым, потом видишь ответ AI\n"
        "🔹 <b>AI Detective</b> — находишь ошибки в ответе AI\n"
        "🔹 <b>Co-Creation</b> — улучшаешь ответ AI",
        reply_markup=battle_format_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(ChallengeStates.choosing_format)


@router.callback_query(ChallengeStates.choosing_format, F.data.startswith("fmt_"))
async def on_format_selected(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    """Выбор формата битвы."""
    fmt_key = callback.data

    if fmt_key == "fmt_random":
        import random
        fmt_key = random.choice(["fmt_human_first", "fmt_ai_detective", "fmt_co_creation"])  # noqa

    format_map = {
        "fmt_human_first": ChallengeFormat.HUMAN_FIRST,
        "fmt_ai_detective": ChallengeFormat.AI_DETECTIVE,
        "fmt_co_creation": ChallengeFormat.CO_CREATION,
    }
    selected_format = format_map.get(fmt_key, ChallengeFormat.HUMAN_FIRST)

    await state.update_data(selected_format=selected_format.value)
    await callback.message.edit_text(
        "🎯 <b>Выбери категорию задания:</b>",
        reply_markup=category_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(ChallengeStates.choosing_category)
    await callback.answer()


@router.message(F.text == "🎯 Выбрать задание")
async def cmd_choose_category(
    message: Message, session: AsyncSession, state: FSMContext
) -> None:
    """Выбор категории задания."""
    if not await _require_registration(message, session):
        return

    await state.clear()
    await state.update_data(selected_format=None)  # Любой формат
    await message.answer(
        "🎯 <b>Выбери категорию:</b>",
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
    data = await state.get_data()
    category = CATEGORY_MAP.get(callback.data)

    service = ChallengeService(session)
    challenge = await service.get_random_challenge(category)

    if not challenge:
        await callback.answer("😔 Заданий не найдено. Попробуй другую категорию.", show_alert=True)
        return

    await state.update_data(challenge_id=challenge.id, start_time=__import__("time").time())

    # Формируем заголовок
    cat_name = CATEGORY_NAMES.get(challenge.category, "🎯 Задание")
    diff_name = DIFFICULTY_DISPLAY.get(challenge.difficulty.value, "🔵")
    fmt_name = FORMAT_DISPLAY.get(challenge.format, "⚔️")

    header = (
        f"{cat_name} | {diff_name}\n"
        f"🎮 Формат: {fmt_name}\n"
        f"⚡ XP: до {challenge.xp_max}\n"
        f"{'⏱ ' + str(challenge.time_limit_seconds // 60) + ' мин' if challenge.time_limit_seconds else ''}\n\n"
    )

    # Если формат AI Detective — показываем ответ AI до ответа пользователя
    ai_prefix = ""
    if challenge.format == ChallengeFormat.AI_DETECTIVE and challenge.ai_response:
        ai_prefix = (
            f"🤖 <b>Ответ AI:</b>\n"
            f"<i>{challenge.ai_response}</i>\n\n"
            f"🔍 <b>Найди ошибку или проблему в ответе AI:</b>\n\n"
        )
    elif challenge.format == ChallengeFormat.CO_CREATION and challenge.ai_response:
        ai_prefix = (
            f"🤖 <b>Начало ответа AI:</b>\n"
            f"<i>{challenge.ai_response}</i>\n\n"
            f"🤝 <b>Улучши и дополни этот ответ:</b>\n\n"
        )

    challenge_text = header + ai_prefix + challenge.description

    if challenge.answer_type == AnswerType.CHOICE:
        options = await service.get_options_list(challenge)
        if options:
            # Формируем текст с вариантами
            letters = ["А", "Б", "В", "Г", "Д"]
            options_text = "\n".join(
                f"{letters[i]}) {opt}" for i, opt in enumerate(options)
            )
            await callback.message.edit_text(
                challenge_text + "\n\n" + options_text,
                reply_markup=options_keyboard(options, challenge.id),
                parse_mode="HTML",
            )
            await state.set_state(ChallengeStates.waiting_for_answer)
        else:
            await callback.message.edit_text(
                challenge_text,
                parse_mode="HTML",
            )
            await state.set_state(ChallengeStates.waiting_for_text_answer)
    else:
        await callback.message.edit_text(
            challenge_text + "\n\n✍️ <b>Введи свой ответ текстом:</b>",
            parse_mode="HTML",
        )
        await state.set_state(ChallengeStates.waiting_for_text_answer)

    await callback.answer()


@router.callback_query(
    ChallengeStates.waiting_for_answer,
    F.data.startswith("answer_"),
)
async def on_choice_answer(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    """Обработка ответа с выбором варианта."""
    parts = callback.data.split("_")
    if len(parts) < 3:
        await callback.answer("Ошибка формата", show_alert=True)
        return

    try:
        challenge_id = int(parts[1])
        selected_index = int(parts[2])
    except ValueError:
        await callback.answer("Ошибка формата", show_alert=True)
        return

    state_data = await state.get_data()
    if state_data.get("challenge_id") != challenge_id:
        await callback.answer("Это задание уже закончилось.", show_alert=True)
        return

    start_time = state_data.get("start_time", 0)
    time_spent = int(__import__("time").time() - start_time)

    service = ChallengeService(session)
    challenge = await service.get_challenge(challenge_id)
    if not challenge:
        await callback.answer("Задание не найдено.", show_alert=True)
        return

    result = await service.submit_choice_answer(
        user_id=callback.from_user.id,
        challenge=challenge,
        selected_index=selected_index,
        time_spent=time_spent,
    )

    await state.clear()
    await _send_result(callback.message, result, challenge, edit=True)
    await callback.answer()


@router.message(ChallengeStates.waiting_for_text_answer)
async def on_text_answer(
    message: Message, session: AsyncSession, state: FSMContext
) -> None:
    """Обработка текстового ответа."""
    if not message.text:
        await message.answer("Отправь текстовый ответ.")
        return

    state_data = await state.get_data()
    challenge_id = state_data.get("challenge_id")
    start_time = state_data.get("start_time", 0)
    time_spent = int(__import__("time").time() - start_time)

    service = ChallengeService(session)
    challenge = await service.get_challenge(challenge_id)
    if not challenge:
        await message.answer("Задание не найдено. Попробуй снова.")
        await state.clear()
        return

    # Показываем что ответ принят
    processing_msg = await message.answer("⏳ Оцениваю твой ответ...")

    try:
        result = await service.submit_text_answer(
            user_id=message.from_user.id,
            challenge=challenge,
            user_answer=message.text,
            time_spent=time_spent,
        )
        await state.clear()
        try:
            await processing_msg.delete()
        except Exception:
            pass
        await _send_result(message, result, challenge, edit=False)
    except Exception as e:
        logger.error(f"Error evaluating text answer: {e}", exc_info=True)
        await state.clear()
        try:
            await processing_msg.delete()
        except Exception:
            pass
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

    # Иконка результата
    if is_correct:
        status_icon = "✅"
        status_text = "Верно!" if score_percent >= 80 else "Принято!"
    else:
        status_icon = "❌"
        status_text = "Неверно"

    score_bar = ""
    if score_percent > 0:
        filled = int(score_percent / 10)
        score_bar = f"\n📊 Оценка: {'█' * filled}{'░' * (10 - filled)} {score_percent:.0f}%"

    xp_text = ""
    if xp_earned > 0 and is_first:
        xp_text = f"\n⚡ +{xp_earned} XP"
    elif not is_first:
        xp_text = "\n💡 XP за повторное прохождение не начисляется"

    result_text = (
        f"{status_icon} <b>{status_text}</b>{score_bar}{xp_text}\n\n"
    )

    if feedback and feedback != explanation:
        result_text += f"💬 {feedback}\n\n"

    if explanation:
        result_text += f"📖 <b>Объяснение:</b>\n{explanation}"

    if level_up and new_level:
        level_icon = LEVEL_ICONS.get(new_level, "🌟")
        level_name = LEVEL_NAMES.get(new_level, "")
        result_text += f"\n\n🎉 <b>ПОВЫШЕНИЕ УРОВНЯ!</b>\n{level_icon} {level_name} (Уровень {new_level})"

    if new_achievements:
        result_text += "\n\n🏅 <b>Новые достижения:</b>"
        for ach in new_achievements:
            result_text += f"\n{ach.icon} <b>{ach.name}</b> +{ach.xp_reward} XP"

    keyboard = after_challenge_keyboard()

    if edit:
        await msg.edit_text(result_text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await msg.answer(result_text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "next_challenge")
async def on_next_challenge(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    """Следующий случайный вызов."""
    await state.clear()
    service = ChallengeService(session)
    challenge = await service.get_random_challenge()

    if not challenge:
        await callback.answer("Заданий нет.", show_alert=True)
        return

    await state.update_data(challenge_id=challenge.id, start_time=__import__("time").time())

    cat_name = CATEGORY_NAMES.get(challenge.category, "🎯")
    diff_name = DIFFICULTY_DISPLAY.get(challenge.difficulty.value, "")

    if challenge.answer_type == AnswerType.CHOICE:
        service2 = ChallengeService(session)
        options = await service2.get_options_list(challenge)
        if options:
            letters = ["А", "Б", "В", "Г", "Д"]
            options_text = "\n".join(f"{letters[i]}) {opt}" for i, opt in enumerate(options))
            await callback.message.edit_text(
                f"{cat_name} | {diff_name}\n⚡ XP: до {challenge.xp_max}\n\n"
                + challenge.description + "\n\n" + options_text,
                reply_markup=options_keyboard(options, challenge.id),
                parse_mode="HTML",
            )
            await state.set_state(ChallengeStates.waiting_for_answer)
            await callback.answer()
            return

    await callback.message.edit_text(
        f"{cat_name} | {diff_name}\n\n" + challenge.description + "\n\n✍️ Введи ответ:",
        parse_mode="HTML",
    )
    await state.set_state(ChallengeStates.waiting_for_text_answer)
    await callback.answer()


@router.callback_query(F.data == "choose_category")
async def on_choose_category_callback(
    callback: CallbackQuery, state: FSMContext
) -> None:
    await state.clear()
    await state.update_data(selected_format=None)
    await callback.message.edit_text(
        "🎯 <b>Выбери категорию:</b>",
        reply_markup=category_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(ChallengeStates.choosing_category)
    await callback.answer()
