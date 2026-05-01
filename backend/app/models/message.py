"""Message model – chat messages within a room."""

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Message(UUIDMixin, TimestampMixin, Base):
    """A single chat message inside a room."""

    __tablename__ = "messages"

    room_id: Mapped[str] = mapped_column(
        ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sender_ip: Mapped[str] = mapped_column(String(45), nullable=False)
    nickname: Mapped[str] = mapped_column(String(50), nullable=False)

    # Relationships
    room: Mapped["Room"] = relationship("Room", back_populates="messages")
