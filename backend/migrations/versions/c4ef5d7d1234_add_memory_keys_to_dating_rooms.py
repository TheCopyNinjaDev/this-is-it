"""add memory keys to dating rooms

Revision ID: c4ef5d7d1234
Revises: b2a1f1b9d321
Create Date: 2026-03-09 00:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4ef5d7d1234"
down_revision: Union[str, Sequence[str], None] = "b2a1f1b9d321"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("dating_rooms", sa.Column("memory_photo_key", sa.String(length=512), nullable=True))
    op.add_column("dating_rooms", sa.Column("memory_postcard_key", sa.String(length=512), nullable=True))


def downgrade() -> None:
    op.drop_column("dating_rooms", "memory_postcard_key")
    op.drop_column("dating_rooms", "memory_photo_key")
