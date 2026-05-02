"""Room schemas for request/response validation."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# Will be overridden dynamically in the API endpoint
DEFAULT_PASSCODE_MIN = 4


class RoomCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    passcode: str = Field(..., min_length=1, max_length=20)
    nickname: str = Field("Anonymous", max_length=50)


class RoomJoin(BaseModel):
    passcode: str = Field(..., min_length=1, max_length=20)
    nickname: str = Field("Anonymous", max_length=50)


class RoomResponse(BaseModel):
    id: UUID
    name: str
    passcode: str
    status: str
    max_members: int
    timeout_minutes: int
    last_activity_at: datetime
    created_at: datetime
    online_count: int = 0

    model_config = {"from_attributes": True}


class RoomSummary(BaseModel):
    id: UUID
    name: str
    status: str
    creator_ip: str
    passcode: str = ""
    online_count: int = 0
    message_count: int = 0
    last_activity_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}
