from fastapi import APIRouter, status

from src.auth import create_access_token, validate_telegram_init_data
from src.schemas.auth import TelegramAuthRequest, TokenResponse

router = APIRouter(
    tags=["Auth"],
    prefix="/auth",
)


@router.post("/telegram", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def authenticate_telegram(request: TelegramAuthRequest) -> TokenResponse:
    payload = validate_telegram_init_data(request.init_data)
    telegram_user = payload["user"]

    return TokenResponse(access_token=create_access_token(user_id=int(telegram_user["id"])))
