"""
Скрипт инициализации и начального наполнения базы данных.
Загружает задания из app/content/challenges.json и достижения из app/content/achievements.json.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    Achievement,
    AnswerType,
    Base,
    Challenge,
    ChallengeCategory,
    ChallengeDifficulty,
    ChallengeFormat,
)
from app.database.session import AsyncSessionFactory, engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CONTENT_DIR = Path(__file__).parent.parent / "content"


async def init_db() -> None:
    """Создание всех таблиц базы данных."""
    logger.info("Initializing database schema...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema initialized successfully.")


async def seed_achievements(session: AsyncSession) -> int:
    """Загрузка достижений из achievements.json."""
    file_path = CONTENT_DIR / "achievements.json"
    if not file_path.exists():
        logger.warning(f"File not found: {file_path}")
        return 0

    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)

    count = 0
    for item in data:
        code = item["code"]
        existing = await session.scalar(select(Achievement).where(Achievement.code == code))

        cond_val = item.get("condition_value")
        if isinstance(cond_val, (dict, list)):
            cond_val = json.dumps(cond_val, ensure_ascii=False)
        elif cond_val is not None:
            cond_val = str(cond_val)

        if existing:
            existing.name = item["name"]
            existing.description = item["description"]
            existing.icon = item.get("icon", "🏅")
            existing.xp_reward = item.get("xp_reward", 50)
            existing.condition_type = item["condition_type"]
            existing.condition_value = cond_val
            existing.is_active = item.get("is_active", True)
        else:
            ach = Achievement(
                code=code,
                name=item["name"],
                description=item["description"],
                icon=item.get("icon", "🏅"),
                xp_reward=item.get("xp_reward", 50),
                condition_type=item["condition_type"],
                condition_value=cond_val,
                is_active=item.get("is_active", True),
            )
            session.add(ach)
            count += 1

    await session.commit()
    logger.info(f"Loaded/updated {len(data)} achievements ({count} new).")
    return len(data)


async def seed_challenges(session: AsyncSession) -> int:
    """Загрузка челленджей из challenges.json."""
    file_path = CONTENT_DIR / "challenges.json"
    if not file_path.exists():
        logger.warning(f"File not found: {file_path}")
        return 0

    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)

    count = 0
    for item in data:
        ext_id = item["external_id"]
        existing = await session.scalar(select(Challenge).where(Challenge.external_id == ext_id))

        options_str = (
            json.dumps(item["options"], ensure_ascii=False) if item.get("options") else None
        )
        tags_str = json.dumps(item["tags"], ensure_ascii=False) if item.get("tags") else None
        crit_val = item.get("evaluation_criteria")
        if isinstance(crit_val, (dict, list)):
            crit_str = json.dumps(crit_val, ensure_ascii=False)
        elif isinstance(crit_val, str):
            crit_str = crit_val
        else:
            crit_str = None

        category_enum = ChallengeCategory(item["category"])
        diff_enum = ChallengeDifficulty(item["difficulty"])
        format_enum = ChallengeFormat(item["format"])
        ans_enum = AnswerType(item["answer_type"])

        if existing:
            existing.title = item["title"]
            existing.category = category_enum
            existing.difficulty = diff_enum
            existing.format = format_enum
            existing.answer_type = ans_enum
            existing.description = item["description"]
            existing.ai_response = item.get("ai_response")
            existing.options = options_str
            existing.correct_answer = item.get("correct_answer")
            existing.explanation = item["explanation"]
            existing.evaluation_criteria = crit_str
            existing.xp_base = item.get("xp_base", 10)
            existing.xp_max = item.get("xp_max", 30)
            existing.time_limit_seconds = item.get("time_limit_seconds")
            existing.tags = tags_str
            existing.source = item.get("source")
            existing.is_daily_eligible = item.get("is_daily_eligible", True)
        else:
            ch = Challenge(
                external_id=ext_id,
                title=item["title"],
                category=category_enum,
                difficulty=diff_enum,
                format=format_enum,
                answer_type=ans_enum,
                description=item["description"],
                ai_response=item.get("ai_response"),
                options=options_str,
                correct_answer=item.get("correct_answer"),
                explanation=item["explanation"],
                evaluation_criteria=crit_str,
                xp_base=item.get("xp_base", 10),
                xp_max=item.get("xp_max", 30),
                time_limit_seconds=item.get("time_limit_seconds"),
                tags=tags_str,
                source=item.get("source"),
                is_daily_eligible=item.get("is_daily_eligible", True),
            )
            session.add(ch)
            count += 1

    await session.commit()
    logger.info(f"Loaded/updated {len(data)} challenges ({count} new).")
    return len(data)


async def seed_data(session: AsyncSession) -> None:
    """Выполняет полное наполнение базы данных."""
    await seed_achievements(session)
    await seed_challenges(session)


async def main() -> None:
    """Главная функция для ручного запуска сидинга."""
    await init_db()
    async with AsyncSessionFactory() as session:
        await seed_data(session)
    logger.info("Database seeding completed successfully.")


if __name__ == "__main__":
    asyncio.run(main())
