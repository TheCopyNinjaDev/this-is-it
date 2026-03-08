from fastapi import APIRouter, Depends, HTTPException, Response, status
from src.schemas.user import UserCreate, UserPatch, UserResponse, UserUpdate
from src.services.user_service import UserService

from src.api.deps import(
    require_bearer_or_jwt_token,
    require_bearer_token,
    get_user_service
)

router = APIRouter(
    tags=["User"],
    prefix="/user",
)

@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: UserCreate,
    service: UserService  = Depends(get_user_service),
    _: None = Depends(require_bearer_token),
) -> UserResponse:
    return await service.create_user(request)

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    service: UserService  = Depends(get_user_service),
    _: dict | None = Depends(require_bearer_or_jwt_token),
) -> UserResponse:
    user = await service.get_user(user_id)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    request: UserUpdate,
    service: UserService = Depends(get_user_service),
    _: dict | None = Depends(require_bearer_or_jwt_token),
) -> UserResponse:
    user = await service.update_user(user_id, request)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def patch_user(
    user_id: int,
    request: UserPatch,
    service: UserService = Depends(get_user_service),
    _: dict | None = Depends(require_bearer_or_jwt_token),
) -> UserResponse:
    user = await service.patch_user(user_id, request)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
    _: dict | None = Depends(require_bearer_or_jwt_token),
) -> Response:
    deleted = await service.delete_user(user_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")

    return Response(status_code=status.HTTP_204_NO_CONTENT)
