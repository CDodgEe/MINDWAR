"""Хендлер рейтинга."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories import UserRepository
from app.keyboards.keyboards import main_menu_keyboard
from app.services.leaderboard_service import LeaderboardService

router = Router()


@router.message(F.text == "🏆 Рейтинг")
@router.message(Command("rating"))
@router.callback_query(F.data == "show_leaderboard")
async def show_leaderboard(event: Message | CallbackQuery, session: AsyncSession) -> None:
    """Показать рейтинг игроков."""
    is_callback = isinstance(event, CallbackQuery)
    user_id = event.from_user.id

    lb_service = LeaderboardService(session)
    entries = await lb_service.get_top(limit=10)
    user_rank = await lb_service.get_user_rank(user_id)

    text = lb_service.format_leaderboard_text(entries)

    if user_rank > 0:
        text += f"\n\n📌 Твоё место: <b>#{user_rank}</b>"

    if is_callback:
        await event.message.edit_text(text, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML")
