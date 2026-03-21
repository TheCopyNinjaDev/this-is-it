"""add free custom date flag to users

Revision ID: c1f8a2b4d5e6
Revises: a7d9e3f1c2b4
Create Date: 2026-03-21 14:40:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c1f8a2b4d5e6"
down_revision: Union[str, Sequence[str], None] = "a7d9e3f1c2b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("free_custom_date_generation", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("users", "free_custom_date_generation")
