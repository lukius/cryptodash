import logging
from datetime import datetime, timezone

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket, token: str) -> bool:
        """Validates the token, accepts the WebSocket, adds to active list.
        Returns False if token is invalid (connection rejected)."""
        from backend.core.exceptions import InvalidSessionError
        from backend.database import async_session
        from backend.services.auth import AuthService

        async with async_session() as db:
            service = AuthService(db)
            try:
                await service.validate_session(token)
            except InvalidSessionError:
                await websocket.close(code=4001, reason="Invalid token")
                return False

        await websocket.accept()
        self._connections.append(websocket)
        return True

    def disconnect(self, websocket: WebSocket) -> None:
        """Removes a WebSocket from the active list."""
        if websocket in self._connections:
            self._connections.remove(websocket)

    async def broadcast(self, event: str, data: dict) -> None:
        """Sends a JSON message to all connected clients."""
        message = {
            "event": event,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        dead: list[WebSocket] = []
        for ws in self._connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)
