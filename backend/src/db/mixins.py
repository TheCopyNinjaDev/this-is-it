from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

NOW_UTC = sa.text("timezone('utc', now())")

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(pg.TIMESTAMP(timezone=True), nullable=False, server_default=NOW_UTC)
    updated_at: Mapped[datetime] = mapped_column(
        pg.TIMESTAMP(timezone=True), nullable=False, server_default=NOW_UTC, server_onupdate=NOW_UTC
    )

class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(pg.TIMESTAMP(timezone=True))