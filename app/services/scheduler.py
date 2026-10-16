"""
Планировщик фоновых задач на базе APScheduler.
Управляет ежедневной ротацией заданий и напоминаниями пользователям.
"""

from __future__ import annotations

import logging

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from app.config import get_settings
from app.database.models import User, UserSettings
from app.database.session import AsyncSessionFactory
from app.services.daily_service import DailyChallengeService

logger = logging.getLogger(__name__)
settings = get_settings()


async def job_rotate_daily_challenge() -> None:
    """Фоновая задача: обновление и предварительная генерация ежедневного задания."""
    logger.info("Executing scheduled daily challenge rotation...")
    try:
        async with AsyncSessionFactory() as session:
            daily_service = DailyChallengeService(session)
            challenge, date_str = await daily_service.get_or_assign_daily()
            await session.commit()
            logger.info(f"Daily challenge for {date_str} successfully rotated: [{challenge.external_id}] {challenge.title}")
    except Exception as e:
        logger.error(f"Error rotating daily challenge: {e}", exc_info=True)


async def job_send_daily_reminders(bot: Bot) -> None:
    """Фоновая задача: отправка мягких напоминаний о ежедневном испытании."""
    logger.info("Checking users for daily challenge reminder...")
    try:
        async with AsyncSessionFactory() as session:
            daily_service = DailyChallengeService(session)
            challenge, date_str = await daily_service.get_or_assign_daily()

            # Ищем пользователей с включенными уведомлениями
            stmt = (
                select(User)
                .join(UserSettings, UserSettings.user_id == User.id)
                .where(
                    UserSettings.notifications_enabled == True,  # noqa
                    User.is_banned == False,  # noqa
                )
            )
            users = (await session.execute(stmt)).scalars().all()

            sent_count = 0
            for user in users:
                completion = await daily_service.get_user_completion(user.id, date_str)
                if not completion:
                    try:
                        await bot.send_message(
                            chat_id=user.id,
                            text=(
                                f"🔥 <b>Привет, {user.display_name}!</b>\n\n"
                                f"Новый ежедневный вызов дня уже готов:\n"
                                f"⚡ <b>«{challenge.title}»</b>\n\n"
                                f"Не дай своей серии из <b>{user.streak_days} дней</b> прерваться! "
                                f"Заходи в <b>/daily</b> и забери бонусный опыт!"
                            ),
                            parse_mode="HTML",
                        )
                        sent_count += 1
                    except Exception:
                        pass

            logger.info(f"Sent daily reminders to {sent_count} users.")
    except Exception as e:
        logger.error(f"Error in daily reminders job: {e}", exc_info=True)


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    """Инициализация и настройка задач планировщика."""
    scheduler = AsyncIOScheduler(timezone=settings.daily_challenge_tz)

    # Ежедневная ротация в заданный час (по умолчанию 09:00)
    scheduler.add_job(
        job_rotate_daily_challenge,
        trigger=CronTrigger(hour=settings.daily_challenge_hour, minute=0),
        id="rotate_daily_challenge",
        name="Rotate daily challenge",
        replace_existing=True,
    )

    # Ежедневное напоминание через 2 часа после ротации (по умолчанию 11:00)
    reminder_hour = (settings.daily_challenge_hour + 2) % 24
    scheduler.add_job(
        job_send_daily_reminders,
        trigger=CronTrigger(hour=reminder_hour, minute=0),
        args=[bot],
        id="send_daily_reminders",
        name="Send daily reminders",
        replace_existing=True,
    )

    return scheduler
