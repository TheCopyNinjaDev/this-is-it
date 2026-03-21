import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.db.mixins import TimestampMixin


class AppConfig(Base, TimestampMixin):
    __tablename__ = "app_config"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, default=1)
    custom_date_price_stars: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
