"""Room API endpoints – create, join, leave, list."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.api.deps import DBSession
from app.config import get_settings
from app.models.message import Message
from app.models.room import Room
from app.models.system_config import SystemConfig
from app.schemas.message import MessageResponse
from app.schemas.room import RoomCreate, RoomJoin, RoomResponse
from app.services.rate_limiter import check_rate_limit, log_action

router = APIRouter(prefix="/rooms", tags=["rooms"])
settings = get_settings()


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def _get_passcode_min_length(db) -> int:
    return await _get_config_int(db, "passcode_min_length", 4)


@router.post("", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(body: RoomCreate, request: Request, db: DBSession):
    """Create a new chat room."""
    ip = _get_client_ip(request)

    # Dynamic passcode min length check
    min_len = await _get_passcode_min_length(db)
    if len(body.passcode) < min_len:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"口令长度至少为 {min_len} 位",
        )

    # Rate limit check
    allowed, count = await check_rate_limit(db, ip, "create_room", "max_rooms_per_hour")
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. You can create up to the configured limit per hour. ({count} used)",
        )

    # Check passcode uniqueness (only among non-destroyed rooms)
    existing = await db.execute(
        select(Room).where(Room.passcode == body.passcode, Room.status != "destroyed")
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A room with this passcode already exists",
        )

    # Get dynamic config
    timeout = await _get_config_int(db, "room_timeout_minutes", settings.DEFAULT_ROOM_TIMEOUT_MINUTES)
    retention = await _get_config_int(db, "message_retention_hours", settings.DEFAULT_MESSAGE_RETENTION_HOURS)

    from datetime import UTC, datetime

    room = Room(
        name=body.name,
        passcode=body.passcode,
        creator_ip=ip,
        timeout_minutes=timeout,
        message_retention_hours=retention,
        last_activity_at=datetime.now(UTC),
    )
    db.add(room)
    await db.flush()

    await log_action(db, ip, "create_room")

    return RoomResponse(
        id=room.id,
        name=room.name,
        passcode=room.passcode,
        status=room.status,
        max_members=room.max_members,
        timeout_minutes=room.timeout_minutes,
        last_activity_at=room.last_activity_at,
        created_at=room.created_at,
        online_count=0,
    )


@router.post("/join", response_model=RoomResponse)
async def join_room(body: RoomJoin, request: Request, db: DBSession):
    """Join an existing room by passcode."""
    ip = _get_client_ip(request)

    # Dynamic passcode min length check
    min_len = await _get_passcode_min_length(db)
    if len(body.passcode) < min_len:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"口令长度至少为 {min_len} 位",
        )

    # Rate limit check
    allowed, count = await check_rate_limit(db, ip, "join_room", "max_joins_per_hour")
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. You can join up to the configured limit per hour. ({count} used)",
        )

    result = await db.execute(
        select(Room).where(Room.passcode == body.passcode, Room.status == "active")
    )
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found or no longer active",
        )

    await log_action(db, ip, "join_room")

    from app.services.connection_manager import manager

    return RoomResponse(
        id=room.id,
        name=room.name,
        passcode=room.passcode,
        status=room.status,
        max_members=room.max_members,
        timeout_minutes=room.timeout_minutes,
        last_activity_at=room.last_activity_at,
        created_at=room.created_at,
        online_count=manager.get_online_count(str(room.id)),
    )


@router.get("/{room_id}", response_model=RoomResponse)
async def get_room(room_id: UUID, db: DBSession):
    """Get room details."""
    result = await db.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()
    if not room or room.status not in ("active", "pending_destroy"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    from app.services.connection_manager import manager

    return RoomResponse(
        id=room.id,
        name=room.name,
        passcode=room.passcode,
        status=room.status,
        max_members=room.max_members,
        timeout_minutes=room.timeout_minutes,
        last_activity_at=room.last_activity_at,
        created_at=room.created_at,
        online_count=manager.get_online_count(str(room.id)),
    )


@router.get("/{room_id}/messages", response_model=list[MessageResponse])
async def get_room_messages(room_id: UUID, db: DBSession, limit: int = 50):
    """Get recent messages from a room (for history sync)."""
    result = await db.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()
    if not room or room.status not in ("active", "pending_destroy"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    result = await db.execute(
        select(Message)
        .where(Message.room_id == room_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    messages = result.scalars().all()
    # Return in chronological order
    return list(reversed(messages))


@router.get("", response_model=list[RoomResponse])
async def list_active_rooms(db: DBSession):
    """List all active rooms (limited info)."""
    result = await db.execute(
        select(Room).where(Room.status == "active").order_by(Room.last_activity_at.desc())
    )
    rooms = result.scalars().all()

    from app.services.connection_manager import manager

    return [
        RoomResponse(
            id=r.id,
            name=r.name,
            passcode="****",  # Hide passcodes in listing
            status=r.status,
            max_members=r.max_members,
            timeout_minutes=r.timeout_minutes,
            last_activity_at=r.last_activity_at,
            created_at=r.created_at,
            online_count=manager.get_online_count(str(r.id)),
        )
        for r in rooms
    ]


async def _get_config_int(db, key: str, default: int) -> int:
    result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
    config = result.scalar_one_or_none()
    if config:
        try:
            return int(config.value)
        except (ValueError, TypeError):
            pass
    return default
