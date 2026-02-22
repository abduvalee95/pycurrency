"""Application settings loaded from environment variables."""

from functools import lru_cache
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized runtime configuration."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Exchange Accounting MVP"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/exchange_db",
        description="Async SQLAlchemy URL for PostgreSQL",
    )

    telegram_bot_token: str = ""

    ai_provider: Literal["openai", "local", "google", "groq", "openrouter", "deepseek"] = "openai"
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    local_llm_base_url: str = "http://localhost:11434/v1"
    local_llm_model: str = "llama3.1:8b"

    groq_api_key: Optional[str] = None
    groq_model: str = "llama-3.1-8b-instant"

    openrouter_api_key: Optional[str] = None
    openrouter_model: str = "openai/gpt-4.1-mini"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_referer: Optional[str] = None
    openrouter_title: Optional[str] = None

    deepseek_api_key: Optional[str] = None
    deepseek_model: str = "deepseek-chat"
    deepseek_base_url: str = "https://api.deepseek.com/v1"

    allowed_telegram_ids: str = ""
    telegram_webapp_enforce: bool = False

    backups_dir: str = "backups"
    backup_hour: int = 23
    backup_minute: int = 55

    base_currency_code: str = "UZS"
    timezone: str = "Asia/Bishkek"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance for dependency injection."""

    return Settings()
