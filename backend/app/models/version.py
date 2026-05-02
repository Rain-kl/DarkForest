"""Application data model version."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AppVersion(Base):
    """Tracks the current data model version."""

    __tablename__ = "version"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    data_model_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
