from fastapi import APIRouter, Depends, status

from src.auth import create_access_token, validate_telegram_init_data
from src.api.deps import get_user_service
from src.schemas.auth import TelegramAuthRequest, TokenResponse
from src.schemas.user import UserCreate
from src.services.user_service import UserService

router = APIRouter(
    tags=["Auth"],
    prefix="/auth",
)


@router.post("/telegram", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def authenticate_telegram(
    request: TelegramAuthRequest,
    user_service: UserService = Depends(get_user_service),
) -> TokenResponse:
    payload = validate_telegram_init_data(request.init_data)
    telegram_user = payload["user"]
    telegram_user_id = int(telegram_user["id"])

    full_name = " ".join(
        part.strip()
        for part in (
            telegram_user.get("first_name", ""),
            telegram_user.get("last_name", ""),
        )
        if isinstance(part, str) and part.strip()
    )
    if not full_name:
        username = telegram_user.get("username")
        full_name = username if isinstance(username, str) and username.strip() else f"user_{telegram_user_id}"

    await user_service.create_user(
        UserCreate(
            id=telegram_user_id,
            name=full_name,
        )
    )

    return TokenResponse(access_token=create_access_token(user_id=telegram_user_id))
