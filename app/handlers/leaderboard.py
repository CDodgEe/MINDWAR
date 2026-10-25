"""Хендлер рейтинга."""

from __future__ import annotations

import contextlib

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.keyboards import leaderboard_keyboard
from app.services.leaderboard_service import LeaderboardService

router = Router()


@router.message(F.text.in_(["🏆 Рейтинг", "🏆 Таблица лидеров", "🏆 Топ"]))
@router.message(Command("rating"))
@router.callback_query(F.data == "show_leaderboard")
async def show_leaderboard(event: Message | CallbackQuery, session: AsyncSession) -> None:
    """Показать рейтинг игроков."""
    if not event.from_user:
        return

    if isinstance(event, CallbackQuery):
        with contextlib.suppress(Exception):
            await event.answer()

    user_id = event.from_user.id
    lb_service = LeaderboardService(session)
    entries = await lb_service.get_top(limit=10)
    user_rank = await lb_service.get_user_rank(user_id)

    text = lb_service.format_leaderboard_text(entries)
    if user_rank > 0:
        text += f"\n\n📌 <b>Твоё место в рейтинге:</b> #{user_rank}"

    if isinstance(event, CallbackQuery) and isinstance(event.message, Message):
        await event.message.edit_text(text, reply_markup=leaderboard_keyboard(), parse_mode="HTML")
    elif isinstance(event, Message):
        await event.answer(text, reply_markup=leaderboard_keyboard(), parse_mode="HTML")
