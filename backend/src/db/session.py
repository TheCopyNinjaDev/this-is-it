from __future__ import annotations

from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from src.config.settings import settings
from src.db.base import AsyncSessionLocal, make_engine
from contextlib import asynccontextmanager

engine = make_engine(settings.DATABASE_URL_asyncpg)
AsyncSessionLocal.configure(bind=engine)

@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session