"""
spidermax_room — MAX ROOM: Virtual Collaboration Space.

A virtual collaborative space where agents and humans meet,
communicate, and work together.

Usage:
    from spidermax_room import Room, Member, RoomEngine

    engine = RoomEngine()
    room = engine.create_room("daily-standup")
    room.join(Member("alice", role=MemberRole.FACILITATOR))
    room.broadcast("alice", {"content": "Meeting starts"})
"""

from .engine import RoomEngine
from .room import Room
from .member import Member, MemberRole, MemberStatus
from .event import RoomEvent, EventType

__all__ = [
    "RoomEngine", "Room",
    "Member", "MemberRole", "MemberStatus",
    "RoomEvent", "EventType",
]

__version__ = "2.0.0"
