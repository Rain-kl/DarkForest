"""Admin API endpoints – room management, config, stats."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import delete, func, select

from app.api.deps import AdminUser, DBSession
from app.models.message import Message
from app.models.room import Room
from app.models.system_config import SystemConfig
from app.models.user import User
from app.schemas.config import ConfigResponse, ConfigUpdate, SystemStats
from app.schemas.message import MessageResponse, WSMessage
from app.schemas.room import RoomSummary
from app.schemas.user import UserCreate, UserPasswordUpdate, UserResponse, UserUpdate
from app.services.connection_manager import manager
from app.services.auth import hash_password

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
                passcode=r.passcode,
            )
        )
    return summaries


@router.post("/rooms/{room_id}/archive", status_code=status.HTTP_200_OK)
async def archive_room(room_id: UUID, db: DBSession, _: AdminUser):
    result = await db.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    if room.status != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Room is not active")

    # Notify users if any are online
    online_count = manager.get_online_count(str(room_id))
    if online_count > 0:
        await manager.broadcast_to_room(
            str(room_id),
            WSMessage(type="system", content="This room has been archived by an admin."),
        )

    room.status = "pending_destroy"
    room.destroyed_at = datetime.now(UTC)
    await db.flush()
    return {"detail": "Room archived successfully"}


@router.post("/rooms/{room_id}/destroy", status_code=status.HTTP_200_OK)
async def destroy_room(room_id: UUID, db: DBSession, _: AdminUser):
    result = await db.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    if room.status == "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Active rooms must be archived before destruction",
        )

    await db.execute(delete(Message).where(Message.room_id == room_id))
    await db.delete(room)
    await db.flush()
    return {"detail": "Room permanently destroyed"}


@router.post("/rooms/{room_id}/restore", status_code=status.HTTP_200_OK)
async def restore_room(room_id: UUID, db: DBSession, _: AdminUser):
    """Restore a destroyed or pending_destroy room back to active."""
    result = await db.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    if room.status == "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Room is already active")

    # Check passcode doesn't conflict with an active room
    existing = await db.execute(
        select(Room).where(
            Room.passcode == room.passcode,
            Room.status != "destroyed",
            Room.id != room.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Passcode is already in use by another active room",
        )

    room.status = "active"
    room.destroyed_at = None
    room.last_activity_at = datetime.now(UTC)
    await db.flush()
    return {"detail": "Room restored successfully"}


@router.get("/rooms/{room_id}/messages", response_model=list[MessageResponse])
async def get_room_messages_admin(room_id: UUID, db: DBSession, _: AdminUser, limit: int = 100):
    """Admin: view messages in any room regardless of status."""
    result = await db.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    result = await db.execute(
        select(Message)
        .where(Message.room_id == room_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    messages = result.scalars().all()
    return list(reversed(messages))


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


async def _admin_count(db: DBSession) -> int:
    result = await db.execute(
        select(func.count()).select_from(User).where(User.role == "admin", User.is_active)
    )
    return result.scalar() or 0


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(body: UserCreate, db: DBSession, _: AdminUser):
    existing = await db.execute(
        select(User).where((User.username == body.username) | (User.email == body.email))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already exists",
        )

    user = User(
        username=body.username,
        email=str(body.email),
        hashed_password=hash_password(body.password),
        nickname=body.nickname or body.username,
        role=body.role,
        is_active=body.is_active,
    )
    db.add(user)
    await db.flush()
    return user


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: UUID, body: UserUpdate, db: DBSession, current_user: AdminUser):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    existing = await db.execute(
        select(User).where(User.email == body.email, User.id != user_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

    demoting_self = user.id == current_user.id and body.role != "admin"
    disabling_self = user.id == current_user.id and not body.is_active
    removes_active_admin = user.role == "admin" and user.is_active and (
        body.role != "admin" or not body.is_active
    )
    removing_last_admin = removes_active_admin and await _admin_count(db) <= 1
    if demoting_self or disabling_self or removing_last_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove the last active admin or disable your own admin access",
        )

    user.email = str(body.email)
    user.nickname = body.nickname or user.username
    user.role = body.role
    user.is_active = body.is_active
    await db.flush()
    return user


@router.put("/users/{user_id}/password", response_model=UserResponse)
async def update_user_password(
    user_id: UUID, body: UserPasswordUpdate, db: DBSession, _: AdminUser
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.hashed_password = hash_password(body.password)
    await db.flush()
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user(user_id: UUID, db: DBSession, current_user: AdminUser):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )
    if user.role == "admin" and user.is_active and await _admin_count(db) <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the last active admin",
        )

    await db.delete(user)
    await db.flush()
    return {"detail": "User deleted successfully"}


@router.put("/users/{user_id}/toggle-active", response_model=UserResponse)
async def toggle_user_active(user_id: UUID, db: DBSession, current_user: AdminUser):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == current_user.id and user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot disable your own account",
        )
    if user.role == "admin" and user.is_active and await _admin_count(db) <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot disable the last active admin",
        )
    user.is_active = not user.is_active
    await db.flush()
    return user
