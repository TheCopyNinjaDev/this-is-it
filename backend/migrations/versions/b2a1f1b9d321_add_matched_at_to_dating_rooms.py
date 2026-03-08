"""add matched_at to dating rooms

Revision ID: b2a1f1b9d321
Revises: 0f3b7f6d4f7a
Create Date: 2026-03-09 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b2a1f1b9d321"
down_revision: Union[str, Sequence[str], None] = "0f3b7f6d4f7a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("dating_rooms", sa.Column("matched_at", postgresql.TIMESTAMP(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("dating_rooms", "matched_at")
