import uuid
from datetime import datetime
from typing import Any

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
    shuffle_seed: Mapped[uuid.UUID | None] = mapped_column(pg.UUID(as_uuid=True), nullable=True)
    memory_photo_key: Mapped[str | None] = mapped_column(sa.String(512), nullable=True)
    memory_postcard_key: Mapped[str | None] = mapped_column(sa.String(512), nullable=True)
    flow_type: Mapped[str | None] = mapped_column(sa.String(32), nullable=True)
    custom_status: Mapped[str | None] = mapped_column(sa.String(32), nullable=True)
    custom_price_stars: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    custom_paid_at: Mapped[datetime | None] = mapped_column(pg.TIMESTAMP(timezone=True), nullable=True)
    custom_payment_charge_id: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    custom_generation_round: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=0,
        server_default=sa.text("0"),
    )
    custom_preferences: Mapped[list[dict[str, Any]]] = mapped_column(
        pg.JSONB,
        nullable=False,
        default=list,
        server_default=sa.text("'[]'::jsonb"),
    )
    custom_options: Mapped[list[dict[str, Any]]] = mapped_column(
        pg.JSONB,
        nullable=False,
        default=list,
        server_default=sa.text("'[]'::jsonb"),
    )
    custom_votes: Mapped[list[dict[str, Any]]] = mapped_column(
        pg.JSONB,
        nullable=False,
        default=list,
        server_default=sa.text("'[]'::jsonb"),
    )
    custom_matched_option: Mapped[dict[str, Any] | None] = mapped_column(
        pg.JSONB,
        nullable=True,
    )
