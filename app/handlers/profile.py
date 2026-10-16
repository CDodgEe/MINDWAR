"""Хендлер профиля, статистики и достижений."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories import AchievementRepository, UserRepository
from app.keyboards.keyboards import main_menu_keyboard, profile_keyboard, settings_keyboard
from app.services.leaderboard_service import LeaderboardService
from app.services.xp_service import (
    LEVEL_ICONS,
    LEVEL_NAMES,
    get_level,
    get_progress_bar,
    get_xp_for_next_level,
)

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text == "👤 Профиль")
@router.message(Command("profile"))
@router.callback_query(F.data == "show_profile")
async def show_profile(event: Message | CallbackQuery, session: AsyncSession) -> None:
    """Показать профиль игрока."""
    is_callback = isinstance(event, CallbackQuery)
    user_id = event.from_user.id

    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)

    if not user:
        text = "👋 Сначала зарегистрируйся — /start"
        if is_callback:
            await event.message.edit_text(text)
            await event.answer()
        else:
            await event.answer(text)
        return

    level = get_level(user.total_xp)
    level_icon = LEVEL_ICONS.get(level, "🌱")
    level_name = LEVEL_NAMES.get(level, "Новичок")
    progress_bar = get_progress_bar(user.total_xp)
    xp_needed, next_threshold = get_xp_for_next_level(user.total_xp)

    accuracy = 0
    if user.total_answers > 0:
        accuracy = int((user.correct_answers / user.total_answers) * 100)

    next_level_text = (
        f"До следующего уровня: {xp_needed} XP"
        if xp_needed > 0
        else "🏆 Максимальный уровень!"
    )

    streak_text = f"🔥 Серия: {user.streak_days} дней" if user.streak_days > 0 else ""

    # Достижения
    ach_repo = AchievementRepository(session)
    user_achievements = await ach_repo.get_user_achievements(user_id)
    ach_count = len(user_achievements)
    ach_preview = " ".join(ua.achievement.icon for ua in user_achievements[:5])

    profile_text = (
        f"👤 <b>{user.display_name}</b>\n\n"
        f"┌─────────────────────────┐\n"
        f"│ {level_icon} {level_name} (Ур. {level})\n"
        f"│ ⚡ XP: <code>{user.total_xp}</code>\n"
        f"│ {progress_bar}\n"
        f"│ {next_level_text}\n"
        f"├─────────────────────────┤\n"
        f"│ 🎯 Заданий: {user.challenges_completed}\n"
        f"│ 🏆 Побед: {user.battles_won}\n"
        f"│ 🎯 Точность: {accuracy}%\n"
        f"│ {streak_text}\n"
        f"├─────────────────────────┤\n"
        f"│ 🎖️ Достижений: {ach_count}\n"
        f"│ {ach_preview or '(нет)'}\n"
        f"└─────────────────────────┘"
    )

    if is_callback:
        await event.message.edit_text(
            profile_text, reply_markup=profile_keyboard(), parse_mode="HTML"
        )
        await event.answer()
    else:
        await event.answer(
            profile_text, reply_markup=profile_keyboard(), parse_mode="HTML"
        )


@router.message(F.text == "📊 Статистика")
@router.callback_query(F.data == "show_stats")
async def show_stats(event: Message | CallbackQuery, session: AsyncSession) -> None:
    """Показать статистику."""
    is_callback = isinstance(event, CallbackQuery)
    user_id = event.from_user.id

    user_repo = UserRepository(session)
    lb_service = LeaderboardService(session)
    user = await user_repo.get_by_id(user_id)

    if not user:
        text = "👋 Сначала зарегистрируйся — /start"
        if is_callback:
            await event.message.edit_text(text)
        else:
            await event.answer(text)
        if is_callback:
            await event.answer()
        return

    rank = await lb_service.get_user_rank(user_id)
    accuracy = 0
    if user.total_answers > 0:
        accuracy = round((user.correct_answers / user.total_answers) * 100, 1)

    win_rate = 0
    if user.battles_total > 0:
        win_rate = round((user.battles_won / user.battles_total) * 100, 1)

    stats_text = (
        f"📊 <b>Статистика — {user.display_name}</b>\n\n"
        f"🏅 Место в рейтинге: <b>#{rank}</b>\n\n"
        f"📌 <b>Задания:</b>\n"
        f"   Выполнено: {user.challenges_completed}\n"
        f"   Правильных: {user.correct_answers} / {user.total_answers}\n"
        f"   Точность: {accuracy}%\n\n"
        f"⚔️ <b>Битвы:</b>\n"
        f"   Побед: {user.battles_won} / {user.battles_total}\n"
        f"   Процент побед: {win_rate}%\n\n"
        f"🔥 <b>Активность:</b>\n"
        f"   Серия дней: {user.streak_days}\n"
        f"   Всего XP: {user.total_xp}\n"
    )

    if is_callback:
        await event.message.edit_text(stats_text, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(stats_text, parse_mode="HTML")


@router.message(F.text == "🎖️ Достижения")
@router.message(Command("achievements"))
@router.callback_query(F.data == "show_achievements")
async def show_achievements(event: Message | CallbackQuery, session: AsyncSession) -> None:
    """Показать достижения."""
    is_callback = isinstance(event, CallbackQuery)
    user_id = event.from_user.id

    ach_repo = AchievementRepository(session)
    user_achievements = await ach_repo.get_user_achievements(user_id)
    all_achievements = await ach_repo.get_all()

    if not user_achievements:
        text = (
            "🎖️ <b>Достижения</b>\n\n"
            "У тебя пока нет достижений.\n"
            "Начни проходить задания, чтобы получить первое! 🚀\n\n"
            f"Всего доступно: {len(all_achievements)} достижений"
        )
    else:
        earned_codes = {ua.achievement.code for ua in user_achievements}
        lines = [f"🎖️ <b>Достижения</b> ({len(user_achievements)}/{len(all_achievements)})\n"]

        for ua in user_achievements:
            ach = ua.achievement
            lines.append(f"{ach.icon} <b>{ach.name}</b> — {ach.description}")

        locked_count = len(all_achievements) - len(user_achievements)
        if locked_count > 0:
            lines.append(f"\n🔒 Ещё {locked_count} достижений ждут тебя!")

        text = "\n".join(lines)

    if is_callback:
        await event.message.edit_text(text, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "settings")
async def show_settings(callback: CallbackQuery, session: AsyncSession) -> None:
    """Настройки профиля."""
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(callback.from_user.id)

    notif_enabled = True
    if user and user.settings:
        notif_enabled = user.settings.notifications_enabled

    await callback.message.edit_text(
        "⚙️ <b>Настройки</b>",
        reply_markup=settings_keyboard(notif_enabled),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "toggle_notifications")
async def toggle_notifications(callback: CallbackQuery, session: AsyncSession) -> None:
    """Переключить уведомления."""
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(callback.from_user.id)

    if user and user.settings:
        user.settings.notifications_enabled = not user.settings.notifications_enabled
        await session.flush()
        status = "включены" if user.settings.notifications_enabled else "выключены"
        await callback.answer(f"🔔 Уведомления {status}", show_alert=True)
        await callback.message.edit_reply_markup(
            reply_markup=settings_keyboard(user.settings.notifications_enabled)
        )


@router.callback_query(F.data == "toggle_leaderboard")
async def toggle_leaderboard(callback: CallbackQuery, session: AsyncSession) -> None:
    """Переключить отображение в рейтинге."""
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(callback.from_user.id)

    if user and user.settings:
        user.settings.show_in_leaderboard = not user.settings.show_in_leaderboard
        await session.flush()
        status = "виден" if user.settings.show_in_leaderboard else "скрыт"
        await callback.answer(f"Рейтинг: ты {status}", show_alert=True)


@router.callback_query(F.data == "delete_account_confirm")
async def delete_account_confirm(callback: CallbackQuery) -> None:
    """Подтверждение удаления аккаунта."""
    from app.keyboards.keyboards import confirm_keyboard
    await callback.message.edit_text(
        "⚠️ <b>Удаление аккаунта</b>\n\n"
        "Все данные (XP, достижения, статистика) будут безвозвратно удалены.\n\n"
        "Ты уверен?",
        reply_markup=confirm_keyboard("delete_account"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "confirm_delete_account")
async def confirm_delete_account(callback: CallbackQuery, session: AsyncSession) -> None:
    """Удаление аккаунта."""
    user_repo = UserRepository(session)
    await user_repo.soft_delete(callback.from_user.id)
    await session.flush()
    await callback.message.edit_text(
        "✅ Аккаунт удалён. Все данные анонимизированы.\n"
        "Если захочешь вернуться — просто напиши /start"
    )
    await callback.answer()


@router.callback_query(F.data == "cancel_action")
async def cancel_action(callback: CallbackQuery) -> None:
    """Отмена действия."""
    await callback.message.delete()
    await callback.answer("Отменено")
