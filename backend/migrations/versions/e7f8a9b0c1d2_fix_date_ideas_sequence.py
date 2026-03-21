"""fix date ideas sequence

Revision ID: e7f8a9b0c1d2
Revises: d4e5f6a7b8c9
Create Date: 2026-03-22 15:40:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e7f8a9b0c1d2"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            SELECT setval(
                pg_get_serial_sequence('date_ideas', 'id'),
                COALESCE((SELECT MAX(id) FROM date_ideas), 1),
                true
            )
            """
        )
    )


def downgrade() -> None:
    pass
