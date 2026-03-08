import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.db.mixins import TimestampMixin


class DatingRoomMemory(Base, TimestampMixin):
    __tablename__ = "dating_room_memories"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    room_id: Mapped[uuid.UUID] = mapped_column(
        pg.UUID(as_uuid=True),
        sa.ForeignKey("dating_rooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploaded_by_user_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    photo_key: Mapped[str] = mapped_column(sa.String(512), nullable=False)
    postcard_key: Mapped[str] = mapped_column(sa.String(512), nullable=False)
    matched_at: Mapped[datetime | None] = mapped_column(pg.TIMESTAMP(timezone=True), nullable=True)
