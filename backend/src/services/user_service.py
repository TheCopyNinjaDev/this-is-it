from src.repositories.user_repo import UserRepository
from src.schemas.user import UserCreate, UserPatch, UserResponse, UserUpdate

class UserService:
    def __init__(self, user_repository: UserRepository):
        self.repository = user_repository

    def _to_user_response(self, user) -> UserResponse:
        return UserResponse(
            id=user.id,
            name=user.name,
            is_deleted=user.deleted_at is not None,
        )

    async def create_user(self, user: UserCreate) -> UserResponse:
        created_user = await self.repository.create(
            telegram_id=user.id,
            name=user.name
        )

        return self._to_user_response(created_user)
    
    async def get_user(self, id: int) -> UserResponse | None:
        user = await self.repository.get(id)
        if user is None:
            return None

        return self._to_user_response(user)

    async def update_user(self, user_id: int, user: UserUpdate) -> UserResponse | None:
        updated_user = await self.repository.update(
            id=user_id,
            name=user.name,
        )
        if updated_user is None:
            return None

        return self._to_user_response(updated_user)

    async def patch_user(self, user_id: int, user: UserPatch) -> UserResponse | None:
        updated_user = await self.repository.update(
            id=user_id,
            name=user.name,
        )
        if updated_user is None:
            return None

        return self._to_user_response(updated_user)

    async def delete_user(self, user_id: int) -> bool:
        user = await self.repository.get(user_id)
        if user is None:
            return False

        await self.repository.soft_delete(user_id)
        return True
