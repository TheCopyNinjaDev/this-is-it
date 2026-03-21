import hmac
from collections.abc import AsyncGenerator
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import decode_access_token
from src.config.settings import settings
from src.db.session import get_session

from src.repositories.room_repo import RoomRepository
from src.repositories.user_repo import UserRepository
from src.storage import ObjectStorage

from src.services.room_service import RoomService
from src.services.openrouter_service import OpenRouterDateGenerator
from src.services.telegram_billing_service import TelegramBillingService
from src.services.user_service import UserService

_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class AuthContext:
    is_service: bool
    user_id: int | None = None

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with get_session() as session:
        yield session

async def get_user_repository(
    session: AsyncSession = Depends(get_async_session),
) -> UserRepository:
    return UserRepository(session)

async def get_user_service(
    user_repository: UserRepository = Depends(get_user_repository),
) -> UserService:
    user_service = UserService(
        user_repository=user_repository,
    )
    return user_service


async def get_room_repository(
    session: AsyncSession = Depends(get_async_session),
) -> RoomRepository:
    return RoomRepository(session)


async def get_room_service(
    room_repository: RoomRepository = Depends(get_room_repository),
    user_repository: UserRepository = Depends(get_user_repository),
) -> RoomService:
    return RoomService(
        room_repository=room_repository,
        user_repository=user_repository,
        storage=ObjectStorage(
            access_key=settings.S3_KEY.get_secret_value() if settings.S3_KEY else None,
            secret_key=settings.S3_SECRET_KEY.get_secret_value() if settings.S3_SECRET_KEY else None,
            bucket_name=settings.S3_BUCKET_NAME,
            endpoint_url=settings.S3_ENDPOINT_URL,
            region_name=settings.S3_REGION,
        ),
        frontend_base_url=settings.FRONTEND_BASE_URL,
        telegram_bot_username=settings.TELEGRAM_BOT_USERNAME,
        telegram_mini_app_short_name=settings.TELEGRAM_MINI_APP_SHORT_NAME,
        openrouter_generator=OpenRouterDateGenerator(
            api_key=settings.OPENROUTER_API_KEY.get_secret_value() if settings.OPENROUTER_API_KEY else None,
            model=settings.OPENROUTER_MODEL,
            base_url=settings.OPENROUTER_BASE_URL,
        ),
        telegram_billing=TelegramBillingService(
            bot_token=settings.TELEGRAM_BOT_TOKEN.get_secret_value(),
            bot_username=settings.TELEGRAM_BOT_USERNAME,
        ),
    )

async def require_bearer_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> None:
    expected = settings.TELEGRAM_BOT_TOKEN.get_secret_value()
    if (
        credentials is None
        or credentials.scheme.lower() != "bearer"
        or not hmac.compare_digest(credentials.credentials, expected)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing bearer token",
        )


async def require_bearer_or_jwt_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> dict | None:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing authorization token",
        )

    expected = settings.TELEGRAM_BOT_TOKEN.get_secret_value()
    if hmac.compare_digest(credentials.credentials, expected):
        return None

    return decode_access_token(credentials.credentials)


async def get_auth_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> AuthContext:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing authorization token",
        )

    expected = settings.TELEGRAM_BOT_TOKEN.get_secret_value()
    if hmac.compare_digest(credentials.credentials, expected):
        return AuthContext(is_service=True)

    payload = decode_access_token(credentials.credentials)
    return AuthContext(is_service=False, user_id=int(payload["sub"]))
