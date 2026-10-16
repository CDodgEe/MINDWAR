"""
Хендлер административной панели бота.
Доступен только пользователям из settings.admin_ids.
"""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database.models import Challenge, ChallengeAttempt, User, XPTransaction
from app.database.repositories import UserRepository
from app.filters.filters import AdminFilter

logger = logging.getLogger(__name__)
router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())

settings = get_settings()


class AdminBroadcastState(StatesGroup):
    waiting_for_message = State()


def admin_panel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура админ-панели."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Общая статистика", callback_data="admin_stats")
    builder.button(text="📢 Рассылка", callback_data="admin_broadcast_start")
    builder.button(text="🔄 Перезагрузить контент", callback_data="admin_reload_content")
    builder.button(text="❌ Закрыть", callback_data="admin_close")
    builder.adjust(1)
    return builder.as_markup()


@router.message(Command("admin"))
async def cmd_admin(message: Message, session: AsyncSession) -> None:
    """Главный экран админ-панели."""
    total_users = await session.scalar(select(func.count(User.id))) or 0
    total_attempts = await session.scalar(select(func.count(ChallengeAttempt.id))) or 0
    total_challenges = await session.scalar(select(func.count(Challenge.id))) or 0

    text = (
        "⚙️ <b>АДМИНИСТРАТИВНАЯ ПАНЕЛЬ AI CHALLENGE</b>\n\n"
        f"🤖 <b>AI Провайдер:</b> <code>{settings.ai_provider}</code> (Модель: <code>{settings.ai_model}</code>)\n"
        f"👥 <b>Всего пользователей:</b> <code>{total_users}</code>\n"
        f"🎯 <b>Активных заданий:</b> <code>{total_challenges}</code>\n"
        f"⚔️ <b>Всего попыток:</b> <code>{total_attempts}</code>\n"
        f"📡 <b>Режим бота:</b> <code>{settings.bot_mode}</code>\n\n"
        "Выберите действие:"
    )
    await message.answer(text, reply_markup=admin_panel_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "admin_stats")
async def admin_stats_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    """Детальная статистика бота."""
    total_users = await session.scalar(select(func.count(User.id))) or 0
    total_attempts = await session.scalar(select(func.count(ChallengeAttempt.id))) or 0
    correct_attempts = await session.scalar(
        select(func.count(ChallengeAttempt.id)).where(ChallengeAttempt.is_correct == True)  # noqa
    ) or 0
    total_xp = await session.scalar(select(func.sum(User.total_xp))) or 0

    winrate = (correct_attempts / total_attempts * 100) if total_attempts > 0 else 0.0

    text = (
        "📊 <b>ДЕТАЛЬНАЯ СТАТИСТИКА СИСТЕМЫ</b>\n\n"
        f"• Пользователей в базе: <b>{total_users}</b>\n"
        f"• Всего сыграно раундов: <b>{total_attempts}</b>\n"
        f"• Успешных решений: <b>{correct_attempts}</b>\n"
        f"• Средний винрейт молодежи: <b>{winrate:.1f}%</b>\n"
        f"• Всего начислено XP: <b>{total_xp:,}</b>\n\n"
        f"🔑 <b>AI Статус:</b> {'🟢 Подключен API' if settings.is_ai_available else '🟡 Mock-режим'}"
    )
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="admin_back")
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_back")
async def admin_back_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    """Возврат в главное меню админки."""
    total_users = await session.scalar(select(func.count(User.id))) or 0
    total_attempts = await session.scalar(select(func.count(ChallengeAttempt.id))) or 0
    total_challenges = await session.scalar(select(func.count(Challenge.id))) or 0

    text = (
        "⚙️ <b>АДМИНИСТРАТИВНАЯ ПАНЕЛЬ AI CHALLENGE</b>\n\n"
        f"🤖 <b>AI Провайдер:</b> <code>{settings.ai_provider}</code> (Модель: <code>{settings.ai_model}</code>)\n"
        f"👥 <b>Всего пользователей:</b> <code>{total_users}</code>\n"
        f"🎯 <b>Активных заданий:</b> <code>{total_challenges}</code>\n"
        f"⚔️ <b>Всего попыток:</b> <code>{total_attempts}</code>\n"
        f"📡 <b>Режим бота:</b> <code>{settings.bot_mode}</code>\n\n"
        "Выберите действие:"
    )
    await callback.message.edit_text(text, reply_markup=admin_panel_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_broadcast_start")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Старт рассылки сообщения."""
    await state.set_state(AdminBroadcastState.waiting_for_message)
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="admin_broadcast_cancel")
    await callback.message.edit_text(
        "📢 <b>Рассылка сообщения</b>\n\n"
        "Отправьте текст сообщения для рассылки всем пользователям бота (поддерживается HTML-разметка).",
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "admin_broadcast_cancel")
async def admin_broadcast_cancel(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Отмена рассылки."""
    await state.clear()
    await admin_back_callback(callback, session)


@router.message(AdminBroadcastState.waiting_for_message)
async def process_broadcast_message(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Отправка рассылки пользователям."""
    broadcast_text = message.html_text or message.text
    await state.clear()

    user_repo = UserRepository(session)
    users = await user_repo.get_all(limit=1000)

    sent = 0
    failed = 0
    status_msg = await message.answer("🚀 Начинаю рассылку...")

    for u in users:
        try:
            await message.bot.send_message(
                chat_id=u.id,
                text=f"📢 <b>Сообщение от AI Challenge:</b>\n\n{broadcast_text}",
                parse_mode="HTML",
            )
            sent += 1
        except Exception:
            failed += 1

    await status_msg.edit_text(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"• Доставлено: <b>{sent}</b>\n"
        f"• Ошибок отправки: <b>{failed}</b>",
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin_reload_content")
async def admin_reload_content(callback: CallbackQuery, session: AsyncSession) -> None:
    """Перезагрузка контента из seed файлов."""
    from app.database.seed import seed_data

    try:
        await seed_data(session)
        await callback.answer("✅ Контент успешно обновлен из JSON файлов!", show_alert=True)
    except Exception as e:
        logger.error(f"Failed to reload content: {e}")
        await callback.answer(f"❌ Ошибка обновления: {e}", show_alert=True)


@router.callback_query(F.data == "admin_close")
async def admin_close(callback: CallbackQuery) -> None:
    """Закрыть панель администратора."""
    await callback.message.delete()
    await callback.answer()
