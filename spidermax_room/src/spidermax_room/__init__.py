"""
spidermax_room — MAX ROOM: Virtual Collaboration Space.

A virtual collaborative space where agents and humans meet,
communicate, and work together — now with real-time WebSocket support.

Usage:
    from spidermax_room import Room, Member, RoomEngine, RoomSocketServer, RoomClient

    # Server
    server = RoomSocketServer(host="0.0.0.0", port=8765)
    server.run()

    # Client
    async with RoomClient("ws://localhost:8765/ws/alice") as client:
        await client.join("my-room")
        await client.broadcast("my-room", {"content": "hello"})
"""

from .engine import RoomEngine
from .room import Room
from .member import Member, MemberRole, MemberStatus
from .event import RoomEvent, EventType
from .server import RoomSocketServer
from .client import RoomClient

__all__ = [
    "RoomEngine", "Room",
    "Member", "MemberRole", "MemberStatus",
    "RoomEvent", "EventType",
    "RoomSocketServer", "RoomClient",
]

__version__ = "2.1.0"
