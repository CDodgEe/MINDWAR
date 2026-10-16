"""Сервис рейтингов и лидерборда."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User
from app.database.repositories import UserRepository
from app.services.xp_service import LEVEL_ICONS, LEVEL_NAMES, get_level


class LeaderboardService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)

    async def get_top(self, limit: int = 10) -> list[dict]:
        """Топ игроков по XP."""
        users = await self.user_repo.get_top_users(limit=limit)
        return [self._format_user(u, i + 1) for i, u in enumerate(users)]

    async def get_user_rank(self, user_id: int) -> int:
        return await self.user_repo.get_user_rank(user_id)

    def _format_user(self, user: User, rank: int) -> dict:
        level = get_level(user.total_xp)
        level_name = LEVEL_NAMES.get(level, "Новичок")
        level_icon = LEVEL_ICONS.get(level, "🌱")

        # Приватность: показываем псевдоним если есть
        display = user.display_name
        if user.settings and user.settings.use_pseudonym and user.settings.pseudonym:
            display = user.settings.pseudonym
        if user.settings and not user.settings.show_in_leaderboard:
            display = "🔒 Скрыт"

        rank_emoji = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"{rank}.")

        return {
            "rank": rank,
            "rank_emoji": rank_emoji,
            "display_name": display,
            "level": level,
            "level_name": level_name,
            "level_icon": level_icon,
            "total_xp": user.total_xp,
            "challenges_completed": user.challenges_completed,
        }

    def format_leaderboard_text(self, entries: list[dict]) -> str:
        if not entries:
            return "Рейтинг пока пуст. Будь первым! 🚀"

        lines = ["🏆 <b>ТОП ИГРОКОВ AI CHALLENGE</b>\n"]
        for e in entries:
            lines.append(
                f"{e['rank_emoji']} <b>{e['display_name']}</b> "
                f"{e['level_icon']} {e['level_name']} • "
                f"<code>{e['total_xp']} XP</code>"
            )
        return "\n".join(lines)
