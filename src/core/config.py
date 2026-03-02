from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Telegram
    bot_token: str

    # Database
    postgres_host: str = "db"
    postgres_port: int = 5432
    postgres_db: str = "rateapp"
    postgres_user: str = "rateapp"
    postgres_password: str = "changeme"
    database_url: str = "postgresql+asyncpg://rateapp:changeme@db:5432/rateapp"

    # Web moderation
    web_admin_user: str = "admin"
    web_admin_password: str = "changeme"
    secret_key: str = "change_this_secret_key_min_32_chars_long"

    # App
    log_level: str = "INFO"


settings = Settings()
