"""Хендлер ежедневного задания."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import AnswerType
from app.database.repositories import UserRepository
from app.keyboards.keyboards import after_challenge_keyboard, main_menu_keyboard, options_keyboard
from app.services.challenge_service import ChallengeService
from app.services.daily_service import DailyChallengeService

logger = logging.getLogger(__name__)
router = Router()


class DailyStates(StatesGroup):
    waiting_for_answer = State()
    waiting_for_text = State()


@router.message(F.text == "🧠 Ежедневный")
@router.message(Command("daily"))
async def cmd_daily(message: Message, session: AsyncSession, state: FSMContext) -> None:
    """Ежедневное задание."""
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(message.from_user.id)

    if not user:
        await message.answer("👋 Сначала зарегистрируйся — /start")
        return

    daily_service = DailyChallengeService(session)
    completion = await daily_service.get_user_completion(message.from_user.id)

    if completion and completion.completed:
        await message.answer(
            "✅ <b>Ежедневное задание выполнено!</b>\n\n"
            f"Ты уже прошёл сегодняшний вызов и получил <code>{completion.xp_earned}</code> XP.\n"
            f"Возвращайся завтра за новым заданием! 🔥\n\n"
            f"Текущая серия: {user.streak_days} 🔥 дней",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML",
        )
        return

    try:
        challenge, date_str = await daily_service.get_or_assign_daily()
    except ValueError as e:
        await message.answer("😔 Ежедневное задание временно недоступно. Попробуй позже.")
        logger.error("Daily challenge error: %s", e)
        return

    await state.update_data(
        challenge_id=challenge.id,
        is_daily=True,
        start_time=__import__("time").time(),
    )

    from app.handlers.challenges import CATEGORY_NAMES, DIFFICULTY_DISPLAY
    cat_name = CATEGORY_NAMES.get(challenge.category, "🎯")
    diff_name = DIFFICULTY_DISPLAY.get(challenge.difficulty.value, "")

    header = (
        f"🧠 <b>ЕЖЕДНЕВНЫЙ ВЫЗОВ</b>\n"
        f"{cat_name} | {diff_name}\n"
        f"⚡ Бонус: +20 XP (+ бонус за серию)\n\n"
    )

    challenge_service = ChallengeService(session)

    if challenge.answer_type == AnswerType.CHOICE:
        options = await challenge_service.get_options_list(challenge)
        if options:
            letters = ["А", "Б", "В", "Г", "Д"]
            options_text = "\n".join(f"{letters[i]}) {opt}" for i, opt in enumerate(options))
            await message.answer(
                header + challenge.description + "\n\n" + options_text,
                reply_markup=options_keyboard(options, challenge.id),
                parse_mode="HTML",
            )
            await state.set_state(DailyStates.waiting_for_answer)
            return

    await message.answer(
        header + challenge.description + "\n\n✍️ Введи свой ответ:",
        parse_mode="HTML",
    )
    await state.set_state(DailyStates.waiting_for_text)


@router.message(DailyStates.waiting_for_text)
async def on_daily_text_answer(
    message: Message, session: AsyncSession, state: FSMContext
) -> None:
    """Обработка текстового ответа ежедневного задания."""
    if not message.text:
        await message.answer("Отправь текстовый ответ.")
        return

    state_data = await state.get_data()
    challenge_id = state_data.get("challenge_id")

    challenge_service = ChallengeService(session)
    daily_service = DailyChallengeService(session)
    challenge = await challenge_service.get_challenge(challenge_id)

    if not challenge:
        await message.answer("Задание не найдено.")
        await state.clear()
        return

    processing_msg = await message.answer("⏳ Оцениваю ответ...")
    result = await challenge_service.submit_text_answer(
        user_id=message.from_user.id,
        challenge=challenge,
        user_answer=message.text,
    )

    # Начисляем ежедневный бонус
    daily_result = await daily_service.mark_daily_complete(
        user_id=message.from_user.id,
        xp_earned=result.get("xp_earned", 0),
    )

    await state.clear()
    await processing_msg.delete()

    is_correct = result.get("is_correct", False)
    xp_earned = result.get("xp_earned", 0)
    daily_bonus = daily_result.get("total_bonus", 0)
    streak = daily_result.get("new_streak", 1)

    result_text = (
        f"{'✅' if is_correct else '❌'} <b>{'Верно!' if is_correct else 'Принято!'}</b>\n\n"
        f"📖 {challenge.explanation}\n\n"
        f"{'🔥' * min(streak, 7)} Серия: {streak} дней\n"
        f"⚡ Очки за задание: +{xp_earned} XP\n"
        f"🎁 Ежедневный бонус: +{daily_bonus} XP"
    )

    await message.answer(
        result_text,
        reply_markup=after_challenge_keyboard(),
        parse_mode="HTML",
    )
