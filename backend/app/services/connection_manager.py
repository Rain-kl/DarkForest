"""WebSocket connection manager for real-time chat."""

import json
from datetime import UTC, datetime

from fastapi import WebSocket
from loguru import logger

from app.schemas.message import WSMessage


class ConnectionManager:
    """Manages active WebSocket connections per room."""

    def __init__(self) -> None:
        # room_id -> set of (websocket, nickname)
        self._connections: dict[str, list[tuple[WebSocket, str]]] = {}

    def connect(self, room_id: str, websocket: WebSocket, nickname: str) -> None:
        """Accept and register a new WebSocket connection."""
        if room_id not in self._connections:
            self._connections[room_id] = []
        self._connections[room_id].append((websocket, nickname))

    def disconnect(self, room_id: str, websocket: WebSocket) -> str | None:
        """Remove a WebSocket connection and return its nickname."""
        if room_id not in self._connections:
            return None
        nickname = None
        self._connections[room_id] = [
            (ws, nick)
            for ws, nick in self._connections[room_id]
            if ws is not websocket
        ]
        # Find the nickname before removal
        for ws, nick in self._connections.get(room_id, []):
            if ws is websocket:
                nickname = nick
                break
        if not self._connections[room_id]:
            del self._connections[room_id]
        return nickname

    def get_online_count(self, room_id: str) -> int:
        """Get the number of active connections in a room."""
        return len(self._connections.get(room_id, []))

    def get_online_nicknames(self, room_id: str) -> list[str]:
        """Get nicknames of all online users in a room."""
        return [nick for _, nick in self._connections.get(room_id, [])]

    def get_room_ids(self) -> list[str]:
        """Get all room IDs with active connections."""
        return list(self._connections.keys())

    async def broadcast_to_room(self, room_id: str, message: WSMessage) -> None:
        """Send a message to all connections in a room."""
        if room_id not in self._connections:
            return
        message.timestamp = datetime.now(UTC)
        data = message.model_dump_json()
        disconnected: list[tuple[WebSocket, str]] = []
        for ws, _ in self._connections[room_id]:
            try:
                await ws.send_text(data)
            except Exception:
                disconnected.append((ws, ""))
        # Clean up disconnected
        for ws, _ in disconnected:
            self.disconnect(room_id, ws)

    async def send_to_user(self, websocket: WebSocket, message: WSMessage) -> None:
        """Send a message to a specific WebSocket connection."""
        message.timestamp = datetime.now(UTC)
        try:
            await websocket.send_text(message.model_dump_json())
        except Exception:
            logger.warning("Failed to send message to websocket")


# Singleton instance
manager = ConnectionManager()
