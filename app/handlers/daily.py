"""Хендлер перенаправления с ежедневных заданий на мгновенную быструю игру."""

from __future__ import annotations

import contextlib

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.handlers.challenges import on_quick_battle

router = Router()


@router.message(Command("daily"))
@router.message(
    F.text.func(
        lambda t: bool(
            t
            and (
                "ежедневн" in t.lower()
                or "daily" in t.lower()
                or t.strip()
                in {
                    "🧠",
                    "🧠 Ежедневный",
                    "🧠 Ежедневный вызов",
                    "🧠 Ежедневное",
                    "🧠 Ежедневное задание",
                }
            )
        )
    )
)
@router.callback_query(F.data == "daily_challenge")
@router.callback_query(F.data.startswith("daily_ans_"))
async def redirect_daily_to_quick(
    event: Message | CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    """Мягкий редирект на Быструю игру для полной совместимости со старыми кнопками."""
    if isinstance(event, CallbackQuery):
        with contextlib.suppress(Exception):
            await event.answer("⚡ Запускаем битву!")
    await on_quick_battle(event, session, state)
