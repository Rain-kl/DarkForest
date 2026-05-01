"""WebSocket endpoint for real-time chat."""

import json
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.message import Message
from app.models.room import Room
from app.schemas.message import WSMessage
from app.services.connection_manager import manager
from app.services.rate_limiter import check_rate_limit

router = APIRouter(tags=["websocket"])


def _get_ws_ip(websocket: WebSocket) -> str:
    forwarded = websocket.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return websocket.client.host if websocket.client else "unknown"


@router.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    """Handle WebSocket connection for a chat room."""
    # Verify room exists and is active
    async with async_session_factory() as db:
        result = await db.execute(
            select(Room).where(Room.id == UUID(room_id), Room.status == "active")
        )
        room = result.scalar_one_or_none()
        if not room:
            await websocket.close(code=4004, reason="Room not found or inactive")
            return

        # Accept connection
        await websocket.accept()

        # Extract info from query params
        nickname = websocket.query_params.get("nickname", "Anonymous")
        ip = _get_ws_ip(websocket)

        # Register connection
        manager.connect(room_id, websocket, nickname)

        # Broadcast join
        await manager.broadcast_to_room(
            room_id,
            WSMessage(
                type="join",
                content=f"{nickname} joined the room",
                nickname=nickname,
                online_count=manager.get_online_count(room_id),
            ),
        )

        # Send welcome
        await manager.send_to_user(
            websocket,
            WSMessage(
                type="system",
                content=f"Welcome to {room.name}! Room will auto-destroy after {room.timeout_minutes} minutes of inactivity.",
            ),
        )

        # Update room activity
        room.last_activity_at = datetime.now(UTC)
        await db.commit()

    try:
        while True:
            data = await websocket.receive_text()
            try:
                parsed = json.loads(data)
                content = parsed.get("content", "").strip()
                msg_type = parsed.get("type", "message")
            except (json.JSONDecodeError, AttributeError):
                content = data.strip()
                msg_type = "message"

            if not content:
                continue

            if msg_type == "ping":
                await manager.send_to_user(websocket, WSMessage(type="pong", content="pong"))
                continue

            # Rate limit check for messages
            async with async_session_factory() as db:
                allowed, _ = await check_rate_limit(
                    db, ip, "send_message", "max_messages_per_minute", window_hours=1/60
                )
                if not allowed:
                    await manager.send_to_user(
                        websocket,
                        WSMessage(type="error", content="Sending messages too fast. Slow down."),
                    )
                    continue

                # Save message
                message = Message(
                    room_id=UUID(room_id),
                    content=content,
                    sender_ip=ip,
                    nickname=nickname,
                )
                db.add(message)

                # Update room activity
                result = await db.execute(select(Room).where(Room.id == UUID(room_id)))
                room_obj = result.scalar_one_or_none()
                if room_obj:
                    room_obj.last_activity_at = datetime.now(UTC)

                await db.commit()

            # Broadcast message
            await manager.broadcast_to_room(
                room_id,
                WSMessage(
                    type="message",
                    content=content,
                    nickname=nickname,
                    online_count=manager.get_online_count(room_id),
                ),
            )

    except WebSocketDisconnect:
        nickname_left = manager.disconnect(room_id, websocket)
        await manager.broadcast_to_room(
            room_id,
            WSMessage(
                type="leave",
                content=f"{nickname_left or 'Someone'} left the room",
                nickname=nickname_left,
                online_count=manager.get_online_count(room_id),
            ),
        )
        logger.info(f"WebSocket disconnected: {nickname_left} from room {room_id}")
    except Exception as e:
        logger.error(f"WebSocket error in room {room_id}: {e}")
        manager.disconnect(room_id, websocket)
