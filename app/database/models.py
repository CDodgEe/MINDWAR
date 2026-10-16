"""
Модели базы данных — SQLAlchemy 2.x с асинхронным доступом.
Полная нормализованная схема PostgreSQL для AI Challenge Bot.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ===================== ENUMS =====================


class ChallengeCategory(str, enum.Enum):
    LOGIC = "logic"
    PROMPT = "prompt"
    DETECTIVE = "detective"
    CREATIVE = "creative"
    CYBER = "cyber"
    REAL_LIFE = "real_life"


class ChallengeDifficulty(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class ChallengeFormat(str, enum.Enum):
    HUMAN_FIRST = "human_first"
    AI_DETECTIVE = "ai_detective"
    CO_CREATION = "co_creation"
    MULTIPLE_CHOICE = "multiple_choice"


class AnswerType(str, enum.Enum):
    TEXT = "text"
    CHOICE = "choice"
    RANKING = "ranking"


class BattleResult(str, enum.Enum):
    WIN = "win"
    LOSE = "lose"
    DRAW = "draw"
    INCOMPLETE = "incomplete"


class XPTransactionType(str, enum.Enum):
    CHALLENGE_COMPLETE = "challenge_complete"
    DAILY_BONUS = "daily_bonus"
    STREAK_BONUS = "streak_bonus"
    ACHIEVEMENT_BONUS = "achievement_bonus"
    CATEGORY_BONUS = "category_bonus"
    LEVEL_UP = "level_up"


# ===================== USERS =====================


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # Telegram user ID
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    language_code: Mapped[str] = mapped_column(String(8), default="ru", nullable=False)

    # Прогресс
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    total_xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Статистика
    challenges_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    battles_won: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    battles_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    correct_answers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_answers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Серия дней
    streak_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_active_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Метаданные
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Связи
    settings: Mapped[Optional[UserSettings]] = relationship(
        "UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    attempts: Mapped[list[ChallengeAttempt]] = relationship(
        "ChallengeAttempt", back_populates="user"
    )
    battle_sessions: Mapped[list[BattleSession]] = relationship(
        "BattleSession", back_populates="user"
    )
    achievements: Mapped[list[UserAchievement]] = relationship(
        "UserAchievement", back_populates="user"
    )
    xp_transactions: Mapped[list[XPTransaction]] = relationship(
        "XPTransaction", back_populates="user"
    )
    daily_challenges: Mapped[list[UserDailyChallenge]] = relationship(
        "UserDailyChallenge", back_populates="user"
    )

    __table_args__ = (Index("ix_users_total_xp", "total_xp"),)

    def __repr__(self) -> str:
        return f"<User id={self.id} name={self.display_name} level={self.level}>"


class UserSettings(Base):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    # Приватность
    show_in_leaderboard: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    use_pseudonym: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    pseudonym: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Уведомления
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    daily_reminder_hour: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Almaty", nullable=False)

    # Связи
    user: Mapped[User] = relationship("User", back_populates="settings")


# ===================== CHALLENGES =====================


class Challenge(Base):
    __tablename__ = "challenges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    category: Mapped[ChallengeCategory] = mapped_column(
        Enum(ChallengeCategory), nullable=False
    )
    difficulty: Mapped[ChallengeDifficulty] = mapped_column(
        Enum(ChallengeDifficulty), nullable=False
    )
    format: Mapped[ChallengeFormat] = mapped_column(Enum(ChallengeFormat), nullable=False)
    answer_type: Mapped[AnswerType] = mapped_column(Enum(AnswerType), nullable=False)

    # Контент
    description: Mapped[str] = mapped_column(Text, nullable=False)
    ai_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # для AI Detective
    options: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON: список вариантов
    correct_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    evaluation_criteria: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON

    # Награды
    xp_base: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    xp_max: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    time_limit_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Метаданные
    tags: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)  # JSON список
    source: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_daily_eligible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Связи
    attempts: Mapped[list[ChallengeAttempt]] = relationship(
        "ChallengeAttempt", back_populates="challenge"
    )
    daily_challenges: Mapped[list[DailyChallenge]] = relationship(
        "DailyChallenge", back_populates="challenge"
    )

    __table_args__ = (
        Index("ix_challenges_category", "category"),
        Index("ix_challenges_difficulty", "difficulty"),
        Index("ix_challenges_active", "is_active"),
    )


class ChallengeAttempt(Base):
    __tablename__ = "challenge_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    challenge_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False
    )

    # Ответ пользователя
    user_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    selected_option: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Результат
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    score_percent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    xp_earned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Метаданные
    time_spent_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_first_attempt: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    xp_rewarded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Связи
    user: Mapped[User] = relationship("User", back_populates="attempts")
    challenge: Mapped[Challenge] = relationship("Challenge", back_populates="attempts")
    battle_session: Mapped[Optional[BattleSession]] = relationship(
        "BattleSession", back_populates="attempt"
    )

    __table_args__ = (
        Index("ix_attempts_user_challenge", "user_id", "challenge_id"),
        Index("ix_attempts_user_id", "user_id"),
        Index("ix_attempts_created_at", "created_at"),
    )


# ===================== BATTLE SESSIONS =====================


class BattleSession(Base):
    __tablename__ = "battle_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    attempt_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("challenge_attempts.id"), nullable=True
    )

    # Формат битвы
    format: Mapped[ChallengeFormat] = mapped_column(Enum(ChallengeFormat), nullable=False)
    result: Mapped[BattleResult] = mapped_column(
        Enum(BattleResult), default=BattleResult.INCOMPLETE, nullable=False
    )

    # AI-ответ для этой битвы
    ai_response_used: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_provider_used: Mapped[str] = mapped_column(String(64), default="mock", nullable=False)

    # Оценки
    user_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    ai_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Связи
    user: Mapped[User] = relationship("User", back_populates="battle_sessions")
    attempt: Mapped[Optional[ChallengeAttempt]] = relationship(
        "ChallengeAttempt", back_populates="battle_session"
    )

    __table_args__ = (Index("ix_battle_sessions_user_id", "user_id"),)


# ===================== ACHIEVEMENTS =====================


class Achievement(Base):
    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    icon: Mapped[str] = mapped_column(String(8), default="🏅", nullable=False)
    xp_reward: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    condition_type: Mapped[str] = mapped_column(String(64), nullable=False)
    condition_value: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)  # JSON
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Связи
    user_achievements: Mapped[list[UserAchievement]] = relationship(
        "UserAchievement", back_populates="achievement"
    )


class UserAchievement(Base):
    __tablename__ = "user_achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    achievement_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("achievements.id"), nullable=False
    )
    earned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Связи
    user: Mapped[User] = relationship("User", back_populates="achievements")
    achievement: Mapped[Achievement] = relationship("Achievement", back_populates="user_achievements")

    __table_args__ = (
        UniqueConstraint("user_id", "achievement_id", name="uq_user_achievement"),
        Index("ix_user_achievements_user_id", "user_id"),
    )


# ===================== XP TRANSACTIONS =====================


class XPTransaction(Base):
    __tablename__ = "xp_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    transaction_type: Mapped[XPTransactionType] = mapped_column(
        Enum(XPTransactionType), nullable=False
    )
    reference_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    description: Mapped[str] = mapped_column(String(256), nullable=False)
    xp_before: Mapped[int] = mapped_column(Integer, nullable=False)
    xp_after: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Связи
    user: Mapped[User] = relationship("User", back_populates="xp_transactions")

    __table_args__ = (
        Index("ix_xp_transactions_user_id", "user_id"),
        Index("ix_xp_transactions_created_at", "created_at"),
    )


# ===================== DAILY CHALLENGES =====================


class DailyChallenge(Base):
    __tablename__ = "daily_challenges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    challenge_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("challenges.id"), nullable=False
    )
    date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD

    # Связи
    challenge: Mapped[Challenge] = relationship("Challenge", back_populates="daily_challenges")
    user_completions: Mapped[list[UserDailyChallenge]] = relationship(
        "UserDailyChallenge", back_populates="daily_challenge"
    )

    __table_args__ = (
        UniqueConstraint("date", name="uq_daily_challenge_date"),
        Index("ix_daily_challenges_date", "date"),
    )


class UserDailyChallenge(Base):
    __tablename__ = "user_daily_challenges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    daily_challenge_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("daily_challenges.id"), nullable=False
    )
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    xp_earned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Связи
    user: Mapped[User] = relationship("User", back_populates="daily_challenges")
    daily_challenge: Mapped[DailyChallenge] = relationship(
        "DailyChallenge", back_populates="user_completions"
    )

    __table_args__ = (
        UniqueConstraint("user_id", "daily_challenge_id", name="uq_user_daily_challenge"),
        Index("ix_user_daily_challenges_user_id", "user_id"),
    )


# ===================== LEADERBOARD SNAPSHOTS =====================


class LeaderboardSnapshot(Base):
    __tablename__ = "leaderboard_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    period: Mapped[str] = mapped_column(String(16), nullable=False)  # 'all', 'weekly', 'YYYY-WNN'
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    xp: Mapped[int] = mapped_column(Integer, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_leaderboard_period_rank", "period", "rank"),
        Index("ix_leaderboard_user_period", "user_id", "period"),
    )
