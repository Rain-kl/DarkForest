"""System config schemas."""

from pydantic import BaseModel, Field


class ConfigUpdate(BaseModel):
    value: str = Field(..., min_length=1)


class ConfigResponse(BaseModel):
    key: str
    value: str
    description: str | None

    model_config = {"from_attributes": True}


class SystemStats(BaseModel):
    total_rooms: int
    active_rooms: int
    pending_destroy_rooms: int
    total_users: int
    total_messages_today: int
