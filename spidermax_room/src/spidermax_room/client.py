"""
RoomClient — WebSocket client for connecting to RoomSocketServer.

Usage:
    async with RoomClient("ws://localhost:8765/ws/alice") as client:
        await client.join("my-room")
        await client.broadcast("my-room", {"content": "hello"})
        events = await client.receive_events()
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from websockets.asyncio.client import connect as ws_connect
from websockets.asyncio.client import ClientConnection

from spidermax_room.member import Member

logger = logging.getLogger(__name__)


class ServerMessage:
    __slots__ = ("type", "data")

    def __init__(self, type: str, data: dict[str, Any]) -> None:
        self.type = type
        self.data = data

    @classmethod
    def from_json(cls, raw: str) -> ServerMessage:
        return cls(type=json.loads(raw).get("type", "unknown"), data=json.loads(raw))


class RoomClient:
    def __init__(self, url: str) -> None:
        self.url = url
        self._ws: ClientConnection | None = None
        self._inbox: asyncio.Queue[ServerMessage] = asyncio.Queue()
        self._connected = False

    async def connect(self) -> None:
        self._ws = await ws_connect(self.url)
        self._connected = True
        asyncio.get_event_loop().create_task(self._reader())
        # Wait for connected ack
        msg = await asyncio.wait_for(self._wait_for_ack("connected"), timeout=5.0)

    async def disconnect(self) -> None:
        if self._ws:
            await self._ws.close()
        self._connected = False

    async def __aenter__(self) -> RoomClient:
        await self.connect()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.disconnect()

    async def _reader(self) -> None:
        try:
            async for raw in self._ws:
                self._inbox.put_nowait(ServerMessage.from_json(raw))
        except Exception:
            pass

    async def _wait_for_ack(self, action: str, timeout: float = 5.0) -> dict:
        deadline = asyncio.get_event_loop().time() + timeout
        while True:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                raise TimeoutError(f"Timeout waiting for: {action}")
            try:
                msg = await asyncio.wait_for(self._inbox.get(), timeout=remaining)
            except asyncio.TimeoutError:
                raise TimeoutError(f"Timeout waiting for: {action}")
            if msg.type == "ack" and msg.data.get("action") == action:
                return msg.data
            if action == "list_rooms" and msg.type == "rooms":
                return msg.data
            if action == "room_status" and msg.type == "status":
                return msg.data
            if msg.type == "error":
                raise RuntimeError(msg.data.get("message", "Server error"))
            # Skip unrelated messages (events from other actions) and keep waiting

    async def _send(self, data: dict) -> None:
        await self._ws.send(json.dumps(data))

    # ── Actions ─────────────────────────────────────────────

    async def join(self, room: str, member: Member | None = None) -> dict:
        msg: dict[str, Any] = {"action": "join", "room": room}
        if member:
            msg["member"] = {"name": member.name, "role": member.role.value}
        await self._send(msg)
        return await self._wait_for_ack("join")

    async def leave(self, room: str | None = None) -> dict:
        await self._send({"action": "leave", "room": room})
        return await self._wait_for_ack("leave")

    async def broadcast(self, room: str, content: Any) -> None:
        await self._send({"action": "broadcast", "room": room, "content": content})

    async def send_to(self, room: str, recipient: str, content: Any) -> None:
        await self._send({"action": "send_to", "room": room, "recipient": recipient, "content": content})

    async def list_rooms(self) -> list[dict]:
        await self._send({"action": "list_rooms"})
        ack = await self._wait_for_ack("list_rooms")
        return ack.get("rooms", [])

    async def room_status(self, room: str) -> dict:
        await self._send({"action": "room_status", "room": room})
        ack = await self._wait_for_ack("room_status")
        return ack.get("room", {})

    # ── Receive ──────────────────────────────────────────────

    async def receive_events(self, count: int = 10, timeout: float = 3.0) -> list[ServerMessage]:
        events: list[ServerMessage] = []
        for _ in range(count):
            try:
                msg = await asyncio.wait_for(self._inbox.get(), timeout=timeout if not events else 0.5)
                if msg.type == "event":
                    events.append(msg)
            except asyncio.TimeoutError:
                break
        return events

    @property
    def connected(self) -> bool:
        return self._connected
