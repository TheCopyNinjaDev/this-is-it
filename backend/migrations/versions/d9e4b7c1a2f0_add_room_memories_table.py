"""add room memories table

Revision ID: d9e4b7c1a2f0
Revises: c4ef5d7d1234
Create Date: 2026-03-09 02:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d9e4b7c1a2f0"
down_revision: Union[str, Sequence[str], None] = "c4ef5d7d1234"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dating_room_memories",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("uploaded_by_user_id", sa.BigInteger(), nullable=False),
        sa.Column("photo_key", sa.String(length=512), nullable=False),
        sa.Column("postcard_key", sa.String(length=512), nullable=False),
        sa.Column("matched_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.ForeignKeyConstraint(["room_id"], ["dating_rooms.id"], name=op.f("fk_dating_room_memories__dating_rooms"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"], name=op.f("fk_dating_room_memories__users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dating_room_memories")),
    )
    op.create_index(op.f("ix_dating_room_memories_room_id"), "dating_room_memories", ["room_id"], unique=False)

    op.execute(
        """
        INSERT INTO dating_room_memories (room_id, uploaded_by_user_id, photo_key, postcard_key, matched_at, created_at, updated_at)
        SELECT
            id,
            creator_user_id,
            memory_photo_key,
            memory_postcard_key,
            matched_at,
            COALESCE(matched_at, updated_at, created_at),
            COALESCE(updated_at, created_at)
        FROM dating_rooms
        WHERE memory_photo_key IS NOT NULL
          AND memory_postcard_key IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_dating_room_memories_room_id"), table_name="dating_room_memories")
    op.drop_table("dating_room_memories")
