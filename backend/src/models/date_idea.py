import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class DateIdea(Base):
    __tablename__ = "date_ideas"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    description: Mapped[str] = mapped_column(sa.Text, nullable=False)
    category: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    vibe: Mapped[str] = mapped_column(sa.String(100), nullable=False)
