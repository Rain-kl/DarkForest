"""Admin API endpoints – room management, config, stats."""

from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import delete, func, select

from app.api.deps import AdminUser, DBSession
from app.models.message import Message
from app.models.room import Room
from app.models.system_config import SystemConfig
from app.models.user import User
from app.schemas.config import ConfigResponse, ConfigUpdate, SystemStats
from app.schemas.room import RoomSummary
from app.schemas.user import UserResponse
from app.services.connection_manager import manager
from app.schemas.message import WSMessage

router = APIRouter(prefix="/admin", tags=["admin"])


# ── Dashboard Stats ──────────────────────────────────────────────────


@router.get("/stats", response_model=SystemStats)
async def get_system_stats(db: DBSession, _: AdminUser):
    total_rooms = await db.execute(select(func.count()).select_from(Room))
    active_rooms = await db.execute(
        select(func.count()).select_from(Room).where(Room.status == "active")
    )
    pending_rooms = await db.execute(
        select(func.count()).select_from(Room).where(Room.status == "pending_destroy")
    )
    total_users = await db.execute(select(func.count()).select_from(User))
    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    msg_today = await db.execute(
        select(func.count()).select_from(Message).where(Message.created_at >= today)
    )
    return SystemStats(
        total_rooms=total_rooms.scalar() or 0,
        active_rooms=active_rooms.scalar() or 0,
        pending_destroy_rooms=pending_rooms.scalar() or 0,
        total_users=total_users.scalar() or 0,
        total_messages_today=msg_today.scalar() or 0,
    )


# ── Room Management ──────────────────────────────────────────────────


@router.get("/rooms", response_model=list[RoomSummary])
async def list_all_rooms(db: DBSession, _: AdminUser, status_filter: str | None = None):
    query = select(Room)
    if status_filter:
        query = query.where(Room.status == status_filter)
    query = query.order_by(Room.created_at.desc())
    result = await db.execute(query)
    rooms = result.scalars().all()

    summaries = []
    for r in rooms:
        msg_count = await db.execute(
            select(func.count()).select_from(Message).where(Message.room_id == r.id)
        )
        summaries.append(
            RoomSummary(
                id=r.id,
                name=r.name,
                status=r.status,
                creator_ip=r.creator_ip,
                online_count=manager.get_online_count(str(r.id)),
                message_count=msg_count.scalar() or 0,
                last_activity_at=r.last_activity_at,
                created_at=r.created_at,
            )
        )
    return summaries


@router.post("/rooms/{room_id}/destroy", status_code=status.HTTP_200_OK)
async def destroy_room(room_id: UUID, db: DBSession, _: AdminUser):
    result = await db.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    if room.status == "destroyed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Room already destroyed")

    # Notify users if any are online
    online_count = manager.get_online_count(str(room_id))
    if online_count > 0:
        await manager.broadcast_to_room(
            str(room_id),
            WSMessage(type="system", content="This room has been destroyed by an admin."),
        )

    # Delete messages and mark room
    await db.execute(delete(Message).where(Message.room_id == room_id))
    room.status = "destroyed"
    room.destroyed_at = datetime.now(UTC)
    await db.flush()
    return {"detail": "Room destroyed successfully"}


# ── Config Management ────────────────────────────────────────────────


@router.get("/configs", response_model=list[ConfigResponse])
async def list_configs(db: DBSession, _: AdminUser):
    result = await db.execute(select(SystemConfig).order_by(SystemConfig.key))
    return result.scalars().all()


@router.put("/configs/{key}", response_model=ConfigResponse)
async def update_config(key: str, body: ConfigUpdate, db: DBSession, _: AdminUser):
    result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
    config = result.scalar_one_or_none()
    if config:
        config.value = body.value
    else:
        config = SystemConfig(key=key, value=body.value)
        db.add(config)
    await db.flush()
    return config


# ── User Management ──────────────────────────────────────────────────


@router.get("/users", response_model=list[UserResponse])
async def list_users(db: DBSession, _: AdminUser):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return result.scalars().all()


@router.put("/users/{user_id}/toggle-active", response_model=UserResponse)
async def toggle_user_active(user_id: UUID, db: DBSession, _: AdminUser):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.is_active = not user.is_active
    await db.flush()
    return user
