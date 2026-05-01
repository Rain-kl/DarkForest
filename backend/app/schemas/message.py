"""Message schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    nickname: str = Field("Anonymous", max_length=50)


class MessageResponse(BaseModel):
    id: UUID
    room_id: UUID
    content: str
    nickname: str
    created_at: datetime

    model_config = {"from_attributes": True}


class WSMessage(BaseModel):
    """Message format for WebSocket communication."""

    type: str  # message / system / join / leave / error
    content: str
    nickname: str | None = None
    online_count: int | None = None
    timestamp: datetime | None = None
