import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base
from src.db.mixins import TimestampMixin
from src.models.service_config import ServiceConfig
from src.models.user import User


class UserServiceGrant(Base, TimestampMixin):
    __tablename__ = "user_service_grants"
    __table_args__ = (
        sa.UniqueConstraint("user_id", "service_code", name="uq_user_service_grants_user_service"),
    )

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    service_code: Mapped[str] = mapped_column(
        sa.String(64),
        sa.ForeignKey("service_config.code", ondelete="CASCADE"),
        nullable=False,
    )
    user: Mapped[User] = relationship()
    service: Mapped[ServiceConfig] = relationship()
