"""Room model – anonymous chat spaces."""

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Room(UUIDMixin, TimestampMixin, Base):
    """A chat room identified by a passcode."""

    __tablename__ = "rooms"
    __table_args__ = (
        # Passcode must be unique among non-destroyed rooms only
        Index(
            "ix_rooms_passcode_active",
            "passcode",
            unique=True,
            postgresql_where=text("status != 'destroyed'"),
            sqlite_where=text("status != 'destroyed'"),
        ),
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    passcode: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False
    )  # active / pending_destroy / destroyed
    creator_ip: Mapped[str] = mapped_column(String(45), nullable=False)
    max_members: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    timeout_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    destroyed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    message_retention_hours: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    # Relationships
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="room", lazy="noload"
    )
