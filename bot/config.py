from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str
    backend_base_url: str = "http://127.0.0.1:8000"
    backend_bearer_token: str
    frontend_base_url: str = "http://localhost:5173"
    telegram_bot_username: str | None = None
    telegram_mini_app_short_name: str | None = None
    s3_key: str | None = None
    s3_secret_key: str | None = None
    s3_bucket_name: str | None = None
    s3_endpoint_url: str = "https://storage.yandexcloud.net"
    s3_region: str = "ru-central1"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
