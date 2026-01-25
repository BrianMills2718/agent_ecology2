"""WebSocket handling for real-time updates."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manage active WebSocket connections."""

    def __init__(self) -> None:
        self._active_connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new connection."""
        await websocket.accept()
        async with self._lock:
            self._active_connections.append(websocket)
        logger.info(
            "WebSocket connected. Total connections: %d", len(self._active_connections)
        )

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a connection."""
        async with self._lock:
            if websocket in self._active_connections:
                self._active_connections.remove(websocket)
        logger.info(
            "WebSocket disconnected. Total connections: %d",
            len(self._active_connections),
        )

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Send a message to all connected clients."""
        if not self._active_connections:
            return

        data = json.dumps(message)
        disconnected: list[WebSocket] = []

        async with self._lock:
            for connection in self._active_connections:
                try:
                    await connection.send_text(data)
                except Exception as e:
                    logger.warning("Failed to send to WebSocket: %s", e)
                    disconnected.append(connection)

            # Clean up disconnected
            for conn in disconnected:
                if conn in self._active_connections:
                    self._active_connections.remove(conn)

    @property
    def connection_count(self) -> int:
        """Number of active connections."""
        return len(self._active_connections)


# Global connection manager
manager = ConnectionManager()


async def websocket_endpoint(
    websocket: WebSocket,
    on_connect: Callable[[], Any] | None = None,
) -> None:
    """WebSocket endpoint handler.

    Args:
        websocket: The WebSocket connection
        on_connect: Optional callback when client connects (can return initial state)
    """
    await manager.connect(websocket)

    try:
        # Send initial state if callback provided
        if on_connect is not None:
            initial_state = on_connect()
            if initial_state:
                await websocket.send_json(initial_state)

        # Keep connection alive and handle incoming messages
        # Note: This is NOT a busy loop. The await asyncio.wait_for() below
        # suspends this coroutine until data arrives or timeout, yielding
        # control to the event loop. This is standard async WebSocket pattern.
        while True:
            try:
                # Receive with timeout to allow periodic checks
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0,  # 30 second timeout
                )

                # Handle ping/pong
                if data == "ping":
                    await websocket.send_text("pong")
                else:
                    # Could handle other client messages here
                    logger.debug("Received WebSocket message: %s", data[:100])

            except asyncio.TimeoutError:
                # Send keepalive ping
                try:
                    await websocket.send_text("ping")
                except Exception:
                    break

    except WebSocketDisconnect:
        logger.info("Client disconnected normally")
    except Exception as e:
        logger.warning("WebSocket error: %s", e)
    finally:
        await manager.disconnect(websocket)


async def broadcast_event(event: dict[str, Any]) -> None:
    """Broadcast an event to all connected WebSocket clients."""
    await manager.broadcast(event)


def get_connection_count() -> int:
    """Get the number of active WebSocket connections."""
    return manager.connection_count
