"""add generic service pricing and grants

Revision ID: d4e5f6a7b8c9
Revises: c1f8a2b4d5e6
Create Date: 2026-03-21 15:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c1f8a2b4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "service_config",
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("price_stars", sa.Integer(), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.PrimaryKeyConstraint("code", name=op.f("pk_service_config")),
    )
    op.create_table(
        "user_service_grants",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("service_code", sa.String(length=64), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.ForeignKeyConstraint(["service_code"], ["service_config.code"], name=op.f("fk_user_service_grants__service_config"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_user_service_grants__users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_service_grants")),
        sa.UniqueConstraint("user_id", "service_code", name="uq_user_service_grants_user_service"),
    )

    op.execute(
        sa.text(
            """
            INSERT INTO service_config (code, name, price_stars)
            VALUES (
                'custom_date_generation',
                'Кастомное свидание',
                (SELECT custom_date_price_stars FROM app_config WHERE id = 1)
            )
            ON CONFLICT (code) DO NOTHING
            """
        )
    )

    op.execute(
        sa.text(
            """
            INSERT INTO user_service_grants (user_id, service_code)
            SELECT id, 'custom_date_generation'
            FROM users
            WHERE free_custom_date_generation IS TRUE
            ON CONFLICT (user_id, service_code) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.drop_table("user_service_grants")
    op.drop_table("service_config")
