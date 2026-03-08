import uuid

import sqlalchemy as sa
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.db.mixins import TimestampMixin


class DatingRoomSwipe(Base, TimestampMixin):
    __tablename__ = "dating_room_swipes"
    __table_args__ = (
        UniqueConstraint("room_id", "user_id", "idea_id", name="uq_room_user_idea_swipe"),
    )

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    room_id: Mapped[uuid.UUID] = mapped_column(
        pg.UUID(as_uuid=True),
        sa.ForeignKey("dating_rooms.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    idea_id: Mapped[int] = mapped_column(
        sa.Integer,
        sa.ForeignKey("date_ideas.id", ondelete="CASCADE"),
        nullable=False,
    )
    liked: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
