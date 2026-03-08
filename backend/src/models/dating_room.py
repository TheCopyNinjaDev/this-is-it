import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.db.mixins import TimestampMixin


class DatingRoom(Base, TimestampMixin):
    __tablename__ = "dating_rooms"

    id: Mapped[uuid.UUID] = mapped_column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    creator_user_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(sa.String(32), nullable=False, server_default=sa.text("'waiting'"))
    matched_idea_id: Mapped[int | None] = mapped_column(
        sa.Integer,
        sa.ForeignKey("date_ideas.id", ondelete="SET NULL"),
        nullable=True,
    )
    matched_at: Mapped[datetime | None] = mapped_column(pg.TIMESTAMP(timezone=True), nullable=True)
    match_revealed_at: Mapped[datetime | None] = mapped_column(pg.TIMESTAMP(timezone=True), nullable=True)
    memory_photo_key: Mapped[str | None] = mapped_column(sa.String(512), nullable=True)
    memory_postcard_key: Mapped[str | None] = mapped_column(sa.String(512), nullable=True)
