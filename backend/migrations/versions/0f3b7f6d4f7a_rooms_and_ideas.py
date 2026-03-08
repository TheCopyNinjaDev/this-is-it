"""rooms and ideas

Revision ID: 0f3b7f6d4f7a
Revises: 8cbb897377c7
Create Date: 2026-03-08 22:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0f3b7f6d4f7a"
down_revision: Union[str, Sequence[str], None] = "8cbb897377c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "date_ideas",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("vibe", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_date_ideas")),
    )
    op.create_table(
        "dating_rooms",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("creator_user_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="waiting", nullable=False),
        sa.Column("matched_idea_id", sa.Integer(), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.ForeignKeyConstraint(["creator_user_id"], ["users.id"], name=op.f("fk_dating_rooms__users"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["matched_idea_id"], ["date_ideas.id"], name=op.f("fk_dating_rooms__date_ideas"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dating_rooms")),
    )
    op.create_table(
        "dating_room_participants",
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.ForeignKeyConstraint(["room_id"], ["dating_rooms.id"], name=op.f("fk_dating_room_participants__dating_rooms"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_dating_room_participants__users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("room_id", "user_id", name=op.f("pk_dating_room_participants")),
    )
    op.create_table(
        "dating_room_swipes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("idea_id", sa.Integer(), nullable=False),
        sa.Column("liked", sa.Boolean(), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.ForeignKeyConstraint(["idea_id"], ["date_ideas.id"], name=op.f("fk_dating_room_swipes__date_ideas"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["room_id"], ["dating_rooms.id"], name=op.f("fk_dating_room_swipes__dating_rooms"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_dating_room_swipes__users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dating_room_swipes")),
        sa.UniqueConstraint("room_id", "user_id", "idea_id", name="uq_room_user_idea_swipe"),
    )
    op.bulk_insert(
        sa.table(
            "date_ideas",
            sa.column("title", sa.String),
            sa.column("description", sa.Text),
            sa.column("category", sa.String),
            sa.column("vibe", sa.String),
        ),
        [
            {
                "title": "Coffee Walk Challenge",
                "description": "Take coffee to go, pick a district, and each of you chooses one spontaneous stop on the route.",
                "category": "City",
                "vibe": "Easygoing",
            },
            {
                "title": "Museum With a Game",
                "description": "Visit a museum and invent awards for the most dramatic, weirdest, and most underrated exhibit.",
                "category": "Culture",
                "vibe": "Curious",
            },
            {
                "title": "Sunset Picnic",
                "description": "Build a small picnic with snacks, a blanket, and a playlist, then rate the sunset like harsh critics.",
                "category": "Outdoor",
                "vibe": "Romantic",
            },
            {
                "title": "Street Food Tour",
                "description": "Pick three unfamiliar places and split one item at each stop so you discover new favorites together.",
                "category": "Food",
                "vibe": "Playful",
            },
            {
                "title": "Bookstore Date",
                "description": "Meet in a bookstore, choose a book for each other under a budget, and explain the pick over tea.",
                "category": "Indoor",
                "vibe": "Warm",
            },
            {
                "title": "Arcade Night",
                "description": "Play a few ridiculous games, keep score, and let the loser choose the post-game dessert spot.",
                "category": "Fun",
                "vibe": "Competitive",
            },
        ],
    )


def downgrade() -> None:
    op.drop_table("dating_room_swipes")
    op.drop_table("dating_room_participants")
    op.drop_table("dating_rooms")
    op.drop_table("date_ideas")
