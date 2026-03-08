import uuid

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.db.mixins import TimestampMixin


class DatingRoomParticipant(Base, TimestampMixin):
    __tablename__ = "dating_room_participants"

    room_id: Mapped[uuid.UUID] = mapped_column(
        pg.UUID(as_uuid=True),
        sa.ForeignKey("dating_rooms.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
