"""add shuffle seed to dating rooms

Revision ID: f6a7b8c9d0e1
Revises: e1a2c3d4f5b6
Create Date: 2026-03-10 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e1a2c3d4f5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("dating_rooms", sa.Column("shuffle_seed", postgresql.UUID(as_uuid=True), nullable=True))


def downgrade() -> None:
    op.drop_column("dating_rooms", "shuffle_seed")
