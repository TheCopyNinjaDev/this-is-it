from __future__ import annotations

from collections import defaultdict
from typing import Any
from uuid import UUID

from fastapi import WebSocket


class RoomConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[UUID, list[WebSocket]] = defaultdict(list)

    async def connect(self, room_id: UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[room_id].append(websocket)

    def disconnect(self, room_id: UUID, websocket: WebSocket) -> None:
        connections = self._connections.get(room_id)
        if not connections:
            return

        if websocket in connections:
            connections.remove(websocket)

        if not connections:
            self._connections.pop(room_id, None)

    def disconnect_all(self, room_id: UUID) -> None:
        self._connections.pop(room_id, None)

    async def send_json(self, websocket: WebSocket, payload: dict[str, Any]) -> None:
        await websocket.send_json(payload)

    async def broadcast(self, room_id: UUID, payload: dict[str, Any]) -> None:
        stale_connections: list[WebSocket] = []
        for websocket in list(self._connections.get(room_id, [])):
            try:
                await websocket.send_json(payload)
            except Exception:
                stale_connections.append(websocket)

        for websocket in stale_connections:
            self.disconnect(room_id, websocket)


room_connection_manager = RoomConnectionManager()
