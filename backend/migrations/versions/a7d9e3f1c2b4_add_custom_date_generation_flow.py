"""add custom date generation flow

Revision ID: a7d9e3f1c2b4
Revises: f6a7b8c9d0e1
Create Date: 2026-03-21 14:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "a7d9e3f1c2b4"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "app_config",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("custom_date_price_stars", sa.Integer(), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_app_config")),
    )
    op.execute(
        sa.text(
            """
            INSERT INTO app_config (id, custom_date_price_stars)
            VALUES (1, NULL)
            ON CONFLICT (id) DO NOTHING
            """
        )
    )

    op.add_column("dating_rooms", sa.Column("flow_type", sa.String(length=32), nullable=True))
    op.add_column("dating_rooms", sa.Column("custom_status", sa.String(length=32), nullable=True))
    op.add_column("dating_rooms", sa.Column("custom_price_stars", sa.Integer(), nullable=True))
    op.add_column("dating_rooms", sa.Column("custom_paid_at", postgresql.TIMESTAMP(timezone=True), nullable=True))
    op.add_column("dating_rooms", sa.Column("custom_payment_charge_id", sa.String(length=255), nullable=True))
    op.add_column(
        "dating_rooms",
        sa.Column("custom_generation_round", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "dating_rooms",
        sa.Column("custom_preferences", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )
    op.add_column(
        "dating_rooms",
        sa.Column("custom_options", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )
    op.add_column(
        "dating_rooms",
        sa.Column("custom_votes", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )
    op.add_column(
        "dating_rooms",
        sa.Column("custom_matched_option", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("dating_rooms", "custom_matched_option")
    op.drop_column("dating_rooms", "custom_votes")
    op.drop_column("dating_rooms", "custom_options")
    op.drop_column("dating_rooms", "custom_preferences")
    op.drop_column("dating_rooms", "custom_generation_round")
    op.drop_column("dating_rooms", "custom_payment_charge_id")
    op.drop_column("dating_rooms", "custom_paid_at")
    op.drop_column("dating_rooms", "custom_price_stars")
    op.drop_column("dating_rooms", "custom_status")
    op.drop_column("dating_rooms", "flow_type")
    op.drop_table("app_config")
