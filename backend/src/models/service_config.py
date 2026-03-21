import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.db.mixins import TimestampMixin


class ServiceConfig(Base, TimestampMixin):
    __tablename__ = "service_config"

    code: Mapped[str] = mapped_column(sa.String(64), primary_key=True)
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    price_stars: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"
