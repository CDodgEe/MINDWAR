"""
AI Challenge Bot — конфигурация приложения.
Использует Pydantic Settings для валидации переменных окружения.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # === Telegram ===
    bot_token: str = ""
    admin_ids: list[int] = []

    @field_validator("admin_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, v: str | list) -> list[int]:
        if isinstance(v, list):
            return [int(i) for i in v]
        if isinstance(v, str) and v:
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        return []

    # === База данных ===
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "ai_challenge"
    postgres_user: str = "ai_challenge_user"
    postgres_password: str = "password"
    database_url: str = ""

    @field_validator("database_url", mode="before")
    @classmethod
    def assemble_db_url(cls, v: str, info) -> str:
        if v:
            if v.startswith("postgres://"):
                v = v.replace("postgres://", "postgresql+asyncpg://", 1)
            elif v.startswith("postgresql://") and not v.startswith("postgresql+asyncpg://"):
                v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
            return v
        data = info.data
        return (
            f"postgresql+asyncpg://{data.get('postgres_user')}:"
            f"{data.get('postgres_password')}@{data.get('postgres_host')}:"
            f"{data.get('postgres_port')}/{data.get('postgres_db')}"
        )

    # === Redis ===
    redis_url: str = "redis://localhost:6379/0"

    # === AI Provider ===
    ai_provider: Literal["openai", "openai_compatible", "mock"] = "mock"
    ai_api_key: str = ""
    ai_api_base_url: str = "https://api.openai.com/v1"
    ai_model: str = "gpt-4o-mini"
    ai_max_tokens: int = 1000
    ai_timeout: int = 30

    # === Режим бота ===
    bot_mode: Literal["polling", "webhook"] = "polling"
    webhook_url: str = ""
    webhook_secret: str = ""
    webhook_port: int = 8080

    # === Логирование ===
    log_level: str = "INFO"

    # === Игровые настройки ===
    daily_challenge_hour: int = 9
    daily_challenge_tz: str = "Asia/Almaty"
    max_requests_per_minute: int = 30

    @property
    def is_ai_available(self) -> bool:
        return self.ai_provider != "mock" and bool(self.ai_api_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
