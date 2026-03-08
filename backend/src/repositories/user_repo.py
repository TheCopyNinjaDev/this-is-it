from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User

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
    
    async def update(
        self,
        id: int,
        name: str | None = None,
    ) -> User | None:
        user = await self.get(id)
        if not user:
            return None

        if name is not None:
            user.name = name


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