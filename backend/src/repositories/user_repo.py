from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.models.user_service_grant import UserServiceGrant

class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, *, telegram_id: int, name: str) -> User:
        stmt = (
            insert(User)
            .values(id=telegram_id, name=name)
            .on_conflict_do_nothing(index_elements=[User.id])
            .returning(User)
        )

        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            user = await self.get(telegram_id)

        await self.session.commit()

        if user is None:
            raise RuntimeError(f"Failed to create or fetch user with telegram_id={telegram_id}")

        return user

    async def get(self, user_id: int) -> User | None:
        stmt = select(User).where(
            User.id == user_id,
        )

        result = await self.session.execute(stmt)

        return result.scalar_one_or_none()

    async def get_many(self, user_ids: list[int]) -> list[User]:
        if not user_ids:
            return []

        stmt = select(User).where(User.id.in_(user_ids))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def has_any_service_grant(self, user_ids: list[int], service_code: str) -> bool:
        if not user_ids:
            return False

        stmt = select(UserServiceGrant.id).where(
            UserServiceGrant.user_id.in_(user_ids),
            UserServiceGrant.service_code == service_code,
        ).limit(1)
        return bool(await self.session.scalar(stmt))

    async def list_active_users(self) -> list[User]:
        stmt = select(User).where(User.deleted_at.is_(None)).order_by(User.created_at.asc(), User.id.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def update(
        self,
        id: int,
        name: str | None = None,
        free_custom_date_generation: bool | None = None,
    ) -> User | None:
        user = await self.get(id)
        if not user:
            return None

        if name is not None:
            user.name = name
        if free_custom_date_generation is not None:
            user.free_custom_date_generation = free_custom_date_generation


        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def soft_delete(self, id: int) -> None:
        stmt = (
            update(User)
            .where(User.id == id, User.deleted_at.is_(None))
            .values(deleted_at=func.timezone("utc", func.now()))
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def revive(self, id: int) -> User | None:
        stmt = (
            update(User)
            .where(User.id == id)
            .values(deleted_at=None)
        )
        await self.session.execute(stmt)
        await self.session.commit()
