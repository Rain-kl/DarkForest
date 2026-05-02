"""Room service – business logic for room management."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.message import Message
from app.models.room import Room
from app.models.system_config import SystemConfig
from app.schemas.message import WSMessage
from app.services.connection_manager import manager

settings = get_settings()


async def get_timeout_minutes(db: AsyncSession) -> int:
    """Get the configured room inactivity timeout."""
    result = await db.execute(
        select(SystemConfig).where(SystemConfig.key == "room_timeout_minutes")
    )
    config = result.scalar_one_or_none()
    if config:
        try:
            return int(config.value)
        except (ValueError, TypeError):
            pass
    return settings.DEFAULT_ROOM_TIMEOUT_MINUTES


async def get_retention_hours(db: AsyncSession) -> int:
    """Get the configured message retention period."""
    result = await db.execute(
        select(SystemConfig).where(SystemConfig.key == "message_retention_hours")
    )
    config = result.scalar_one_or_none()
    if config:
        try:
            return int(config.value)
        except (ValueError, TypeError):
            pass
    return settings.DEFAULT_MESSAGE_RETENTION_HOURS


async def update_room_activity(db: AsyncSession, room_id: str) -> None:
    """Refresh last_activity_at for a room."""
    result = await db.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()
    if room:
        room.last_activity_at = datetime.now(UTC)
        await db.flush()


async def cleanup_inactive_rooms(db: AsyncSession) -> int:
    """
    Background task: find inactive rooms, notify users, and mark for destruction.
    Returns the number of rooms processed.
    """
    timeout = await get_timeout_minutes(db)
    cutoff = datetime.now(UTC) - timedelta(minutes=timeout)

    # Find active rooms with no activity
    result = await db.execute(
        select(Room).where(Room.status == "active", Room.last_activity_at < cutoff)
    )
    rooms = result.scalars().all()

    count = 0
    for room in rooms:
        # Notify online users
        online_count = manager.get_online_count(str(room.id))
        if online_count > 0:
            await manager.broadcast_to_room(
                str(room.id),
                WSMessage(
                    type="system",
                    content=f"Room has been inactive for {timeout} minutes and will be destroyed.",
                ),
            )
        room.status = "pending_destroy"
        room.destroyed_at = datetime.now(UTC)
        count += 1

    await db.flush()
    return count


async def destroy_pending_rooms(db: AsyncSession) -> int:
    """
    Permanently destroy rooms that have been pending for longer than retention period.
    """
    retention = await get_retention_hours(db)
    cutoff = datetime.now(UTC) - timedelta(hours=retention)

    # Find pending_destroy rooms past retention
    result = await db.execute(
        select(Room).where(Room.status == "pending_destroy", Room.destroyed_at < cutoff)
    )
    rooms = result.scalars().all()

    count = 0
    for room in rooms:
        await db.execute(delete(Message).where(Message.room_id == room.id))
        await db.delete(room)
        count += 1

    await db.flush()
    return count
