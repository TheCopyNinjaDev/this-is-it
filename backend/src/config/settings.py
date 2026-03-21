from pydantic import SecretStr, model_validator
from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from urllib.parse import quote

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"

class Settings(BaseSettings):

    POSTGRES_HOST: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: SecretStr
    POSTGRES_DB: str

    TELEGRAM_BOT_TOKEN: SecretStr
    TELEGRAM_BOT_USERNAME: str | None = None
    TELEGRAM_MINI_APP_SHORT_NAME: str | None = None
    JWT_SECRET_KEY: SecretStr | None = None
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7
    TELEGRAM_INIT_DATA_TTL_SECONDS: int = 3600
    FRONTEND_BASE_URL: str = "http://localhost:5173"
    ADMIN_USERNAME: str | None = None
    ADMIN_PASSWORD: SecretStr | None = None
    S3_KEY: SecretStr | None = None
    S3_SECRET_KEY: SecretStr | None = None
    S3_BUCKET_NAME: str | None = None
    S3_ENDPOINT_URL: str = "https://storage.yandexcloud.net"
    S3_REGION: str = "ru-central1"
    OPENROUTER_API_KEY: SecretStr | None = None
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = "qwen/qwen3-30b-a3b"
    TELEGRAM_PROXY: str | None = None
    TELEGRAM_PROXY_TYPE: str = "socks5"

    @property
    def DATABASE_URL_asyncpg(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD.get_secret_value()}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def DATABASE_URL_psycopg(self) -> str:
        return f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD.get_secret_value()}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def JWT_SECRET(self) -> SecretStr:
        return self.JWT_SECRET_KEY or self.TELEGRAM_BOT_TOKEN

    @property
    def TELEGRAM_PROXY_URL(self) -> str | None:
        if not self.TELEGRAM_PROXY:
            return None
        if "://" in self.TELEGRAM_PROXY:
            return self.TELEGRAM_PROXY

        parts = self.TELEGRAM_PROXY.split(":", 3)
        if len(parts) != 4:
            raise ValueError("TELEGRAM_PROXY must be in format IP:PORT:LOGIN:PASSWORD")

        host, port, username, password = parts
        scheme = "socks5" if self.TELEGRAM_PROXY_TYPE.lower().startswith("socks") else "http"
        return f"{scheme}://{quote(username, safe='')}:{quote(password, safe='')}@{host}:{port}"

    @model_validator(mode="after")
    def validate_proxy_settings(self) -> "Settings":
        if self.TELEGRAM_PROXY:
            _ = self.TELEGRAM_PROXY_URL
        return self


    model_config = SettingsConfigDict(
        env_file=str(DEFAULT_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

@lru_cache
def get_settings() -> Settings:
    return Settings(**{})

settings = get_settings()
