"""
RoomSocketServer — WebSocket server for real-time room collaboration.

Protocols:
    Client → Server: JSON messages with "action" field
    Server → Client: JSON messages with "type" field (event type) + data

Message format (client → server):
    {"action": "join", "room": "my-room", "member": {...}}
    {"action": "leave", "room": "my-room"}
    {"action": "broadcast", "room": "my-room", "content": "hello"}
    {"action": "send_to", "room": "my-room", "recipient": "bob", "content": "hi"}
    {"action": "subscribe", "room": "my-room"}       # subscribe to all room events
    {"action": "unsubscribe", "room": "my-room"}
    {"action": "list_rooms"}
    {"action": "room_status", "room": "my-room"}

Message format (server → client):
    {"type": "event", "event": {...}}       # room event
    {"type": "error", "message": "..."}      # error message
    {"type": "ack", "action": "..."}         # action acknowledged
    {"type": "rooms", "rooms": [...]}        # room list
    {"type": "status", "room": {...}}        # room status
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from uvicorn import Config, Server

from spidermax_room.room import Room
from spidermax_room.member import Member, MemberRole, MemberStatus
from spidermax_room.event import EventType, RoomEvent

logger = logging.getLogger(__name__)


@dataclass
class ClientConnection:
    """A connected WebSocket client."""
    websocket: WebSocket
    member_name: str | None = None
    current_room: str | None = None


class RoomSocketServer:
    """
    WebSocket server that manages rooms and routes messages.

    Usage:
        server = RoomSocketServer(host="0.0.0.0", port=8765)
        server.run()

    Or with FastAPI:
        app = server.create_app()
        uvicorn.run(app, host="0.0.0.0", port=8765)
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8765) -> None:
        self.host = host
        self.port = port
        self._rooms: dict[str, Room] = {}
        self._clients: dict[str, ClientConnection] = {}  # client_id -> connection
        self._app = FastAPI(title="MAX ROOM", version="2.1.0")
        self._setup_routes()

    @property
    def app(self) -> FastAPI:
        return self._app

    # ── Room CRUD ────────────────────────────────────────────

    def get_or_create_room(self, name: str) -> Room:
        if name not in self._rooms:
            self._rooms[name] = Room(name)
        return self._rooms[name]

    def get_room(self, name: str) -> Room | None:
        return self._rooms.get(name)

    # ── Connection Management ────────────────────────────────

    def _setup_routes(self) -> None:
        @self._app.websocket("/ws/{client_id}")
        async def websocket_endpoint(websocket: WebSocket, client_id: str) -> None:
            await websocket.accept()
            conn = ClientConnection(websocket=websocket)
            self._clients[client_id] = conn
            logger.info("Client connected: %s", client_id)
            # Send connected ack
            await websocket.send_text(json.dumps({"type": "ack", "action": "connected"}))

            try:
                async for raw in self._handle_client_messages(client_id, websocket):
                    pass
            except WebSocketDisconnect:
                pass
            finally:
                await self._cleanup_client(client_id)
                logger.info("Client disconnected: %s", client_id)

    async def _handle_client_messages(self, client_id: str, websocket: WebSocket):
        async for message in websocket.iter_text():
            await self._handle_message(client_id, message)
            yield message

    async def _handle_message(self, client_id: str, raw: str) -> None:
        conn = self._clients.get(client_id)
        if not conn:
            return

        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            await self._send_error(client_id, "Invalid JSON")
            return

        action = msg.get("action")
        if not action:
            await self._send_error(client_id, "Missing 'action' field")
            return

        handler = self._action_handlers.get(action)
        if not handler:
            await self._send_error(client_id, f"Unknown action: {action}")
            return

        try:
            await handler(self, client_id, msg)
        except Exception as e:
            logger.exception("Error handling action '%s'", action)
            await self._send_error(client_id, str(e))

    async def _cleanup_client(self, client_id: str) -> None:
        conn = self._clients.pop(client_id, None)
        if conn and conn.current_room and conn.member_name:
            room = self._rooms.get(conn.current_room)
            if room:
                room.leave(conn.member_name)

    # ── Action Handlers ──────────────────────────────────────

    async def _handle_join(self, client_id: str, msg: dict) -> None:
        conn = self._clients[client_id]
        room_name = msg.get("room")
        member_data = msg.get("member", {})
        member_name = member_data.get("name", client_id)

        room = self.get_or_create_room(room_name)
        role = MemberRole(member_data.get("role", "participant"))
        member = Member(name=member_name, role=role)
        room.join(member)

        conn.member_name = member_name
        conn.current_room = room_name

        await self._send_ack(client_id, "join", room=room_name)
        await self._broadcast_to_room(room_name, {
            "type": "event",
            "event": {
                "type": EventType.MEMBER_JOINED.value,
                "sender": member_name,
                "data": {"member": {"name": member_name, "role": role.value}}
            }
        }, exclude=client_id)

    async def _handle_leave(self, client_id: str, msg: dict) -> None:
        conn = self._clients[client_id]
        room_name = msg.get("room", conn.current_room)
        if not room_name or not conn.member_name:
            await self._send_error(client_id, "Not in a room")
            return

        room = self._rooms.get(room_name)
        if room:
            room.leave(conn.member_name)
            await self._broadcast_to_room(room_name, {
                "type": "event",
                "event": {
                    "type": EventType.MEMBER_LEFT.value,
                    "sender": conn.member_name,
                    "data": {}
                }
            })

        conn.member_name = None
        conn.current_room = None
        await self._send_ack(client_id, "leave", room=room_name)

    async def _handle_broadcast(self, client_id: str, msg: dict) -> None:
        conn = self._clients[client_id]
        room_name = msg.get("room", conn.current_room)
        if not room_name or not conn.member_name:
            await self._send_error(client_id, "Not in a room")
            return

        room = self._rooms.get(room_name)
        if not room:
            await self._send_error(client_id, f"Room not found: {room_name}")
            return

        content = msg.get("content", {})
        room.broadcast(conn.member_name, content)

        await self._broadcast_to_room(room_name, {
            "type": "event",
            "event": {
                "type": EventType.MESSAGE.value,
                "sender": conn.member_name,
                "data": content
            }
        })

    async def _handle_send_to(self, client_id: str, msg: dict) -> None:
        conn = self._clients[client_id]
        room_name = msg.get("room", conn.current_room)
        recipient = msg.get("recipient")
        if not room_name or not conn.member_name or not recipient:
            await self._send_error(client_id, "Missing room, member name, or recipient")
            return

        room = self._rooms.get(room_name)
        if not room:
            await self._send_error(client_id, f"Room not found: {room_name}")
            return

        content = msg.get("content", {})
        room.send_to(conn.member_name, recipient, {**content, "recipient": recipient})

        # Send to recipient
        await self._send_to_member(room_name, recipient, {
            "type": "event",
            "event": {
                "type": EventType.MESSAGE.value,
                "sender": conn.member_name,
                "data": {**content, "recipient": recipient}
            }
        })
        await self._send_ack(client_id, "send_to", recipient=recipient)

    async def _handle_subscribe(self, client_id: str, msg: dict) -> None:
        conn = self._clients[client_id]
        room_name = msg.get("room", conn.current_room)
        if not room_name:
            await self._send_error(client_id, "Not in a room")
            return
        await self._send_ack(client_id, "subscribe", room=room_name)

    async def _handle_list_rooms(self, client_id: str, msg: dict) -> None:
        rooms = []
        for name, room in self._rooms.items():
            rooms.append({
                "name": name,
                "members": room.member_count,
                "online": self._count_online_in_room(name)
            })
        await self._send(client_id, {"type": "rooms", "rooms": rooms})

    async def _handle_room_status(self, client_id: str, msg: dict) -> None:
        room_name = msg.get("room")
        room = self._rooms.get(room_name)
        if not room:
            await self._send_error(client_id, f"Room not found: {room_name}")
            return
        await self._send(client_id, {
            "type": "status",
            "room": {
                "name": room.name,
                "members": room.member_count,
                "online": self._count_online_in_room(room_name)
            }
        })

    # ── Internal messaging ───────────────────────────────────

    async def _send(self, client_id: str, data: dict) -> None:
        conn = self._clients.get(client_id)
        if conn:
            try:
                await conn.websocket.send_text(json.dumps(data))
            except Exception:
                pass

    async def _send_ack(self, client_id: str, action: str, **extra) -> None:
        await self._send(client_id, {"type": "ack", "action": action, **extra})

    async def _send_error(self, client_id: str, message: str) -> None:
        await self._send(client_id, {"type": "error", "message": message})

    async def _broadcast_to_room(self, room_name: str, data: dict, exclude: str | None = None) -> None:
        for cid, conn in self._clients.items():
            if cid == exclude:
                continue
            if conn.current_room == room_name:
                await self._send(cid, data)

    async def _send_to_member(self, room_name: str, member_name: str, data: dict) -> None:
        for cid, conn in self._clients.items():
            if conn.current_room == room_name and conn.member_name == member_name:
                await self._send(cid, data)
                break

    def _count_online_in_room(self, room_name: str) -> int:
        return sum(
            1 for c in self._clients.values()
            if c.current_room == room_name
        )

    # ── Action handler registry ──────────────────────────────

    _action_handlers: dict[str, Any] = {}  # populated after class body

    def run(self) -> None:
        """Run the server (blocking)."""
        config = Config(app=self._app, host=self.host, port=self.port, log_level="info")
        server = Server(config)
        logger.info("MAX ROOM WebSocket server starting on %s:%d", self.host, self.port)
        server.run()


RoomSocketServer._action_handlers = {
    "join": RoomSocketServer._handle_join,
    "leave": RoomSocketServer._handle_leave,
    "broadcast": RoomSocketServer._handle_broadcast,
    "send_to": RoomSocketServer._handle_send_to,
    "subscribe": RoomSocketServer._handle_subscribe,
    "unsubscribe": RoomSocketServer._handle_subscribe,
    "list_rooms": RoomSocketServer._handle_list_rooms,
    "room_status": RoomSocketServer._handle_room_status,
}
