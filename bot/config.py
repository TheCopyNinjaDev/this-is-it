from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    bot_token: str = Field(validation_alias=AliasChoices("BOT_TOKEN", "TELEGRAM_BOT_TOKEN"))
    backend_base_url: str = "http://127.0.0.1:8000"
    backend_bearer_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices("BACKEND_BEARER_TOKEN", "TELEGRAM_BOT_TOKEN"),
    )
    frontend_base_url: str = "http://localhost:5173"
    telegram_bot_username: str | None = None
    telegram_mini_app_short_name: str | None = None
    broadcast_codeword: str | None = None
    s3_key: str | None = None
    s3_secret_key: str | None = None
    s3_bucket_name: str | None = None
    s3_endpoint_url: str = "https://storage.yandexcloud.net"
    s3_region: str = "ru-central1"

    model_config = SettingsConfigDict(
        env_file=str(DEFAULT_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def apply_backend_defaults(self) -> "Settings":
        if self.backend_bearer_token is None:
            self.backend_bearer_token = self.bot_token
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
