"""System config model – dynamic runtime settings."""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SystemConfig(TimestampMixin, Base):
    """Key-value store for dynamic system configuration."""

    __tablename__ = "system_configs"

    key: Mapped[str] = mapped_column(
        String(100), primary_key=True, nullable=False
    )
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
