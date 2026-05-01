"""Rate limit log model – track IP-based actions."""

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class RateLimitLog(Base):
    """Tracks per-IP action counts for rate limiting."""

    __tablename__ = "rate_limit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ip_address: Mapped[str] = mapped_column(String(45), index=True, nullable=False)
    action: Mapped[str] = mapped_column(String(50), index=True, nullable=False)  # create_room / join_room
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
