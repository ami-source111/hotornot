from __future__ import annotations

from pathlib import Path

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Telegram
    bot_token: str

    # Database — individual parts; database_url is derived automatically.
    postgres_host: str = "db"
    postgres_port: int = 5432
    postgres_db: str = "rateapp"
    postgres_user: str = "rateapp"
    postgres_password: str = "changeme"

    @computed_field  # type: ignore[misc]
    @property
    def database_url(self) -> str:
        """Async SQLAlchemy URL constructed from individual DB settings."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # Web moderation
    web_admin_user: str = "admin"
    web_admin_password: str = "changeme"
    secret_key: str = "change_this_secret_key_min_32_chars_long"

    # Shared media storage (mounted volume, same path in both web and bot containers)
    media_dir: Path = Path("/app/media")

    # App
    log_level: str = "INFO"


settings = Settings()

# Ensure media directory exists on startup.
settings.media_dir.mkdir(parents=True, exist_ok=True)
