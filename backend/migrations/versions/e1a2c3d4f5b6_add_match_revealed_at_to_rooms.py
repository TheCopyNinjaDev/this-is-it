"""add match revealed at to rooms

Revision ID: e1a2c3d4f5b6
Revises: d9e4b7c1a2f0
Create Date: 2026-03-09 02:40:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "e1a2c3d4f5b6"
down_revision: Union[str, Sequence[str], None] = "d9e4b7c1a2f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("dating_rooms", sa.Column("match_revealed_at", postgresql.TIMESTAMP(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("dating_rooms", "match_revealed_at")
