"""
Room — a virtual collaboration space.

Members join, communicate, and collaborate inside a room.
All interactions are event-driven.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from .member import Member, MemberStatus
from .event import EventType, RoomEvent

logger = logging.getLogger(__name__)

EventHandler = Callable[[RoomEvent], None]


class Room:
    """A virtual collaboration space where members meet and work together."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._members: dict[str, Member] = {}
        self._handlers: dict[EventType | str, list[EventHandler]] = {}
        self._history: list[RoomEvent] = []

    def join(self, member: Member) -> RoomEvent:
        self._members[member.name] = member
        return self._emit(EventType.MEMBER_JOINED, member.name, {"member": member})

    def leave(self, member_name: str) -> RoomEvent | None:
        if member_name not in self._members:
            return None
        del self._members[member_name]
        return self._emit(EventType.MEMBER_LEFT, member_name, {})

    def set_status(self, member_name: str, status: MemberStatus) -> RoomEvent | None:
        if member_name not in self._members:
            return None
        self._members[member_name].status = status
        return self._emit(EventType.MEMBER_STATUS_CHANGED, member_name, {"status": status})

    def get_member(self, name: str) -> Member | None:
        return self._members.get(name)

    @property
    def members(self) -> dict[str, Member]:
        return dict(self._members)

    @property
    def member_count(self) -> int:
        return len(self._members)

    def broadcast(self, sender: str, data: dict[str, Any]) -> RoomEvent | None:
        if sender not in self._members:
            return None
        return self._emit(EventType.MESSAGE, sender, data)

    def send_to(self, sender: str, recipient: str, data: dict[str, Any]) -> RoomEvent | None:
        if sender not in self._members or recipient not in self._members:
            return None
        data["recipient"] = recipient
        return self._emit(EventType.MESSAGE, sender, data)

    def on_event(self, handler: EventHandler, event_type: EventType | str | None = None) -> None:
        key = event_type if event_type else "*"
        if key not in self._handlers:
            self._handlers[key] = []
        self._handlers[key].append(handler)

    @property
    def history(self) -> list[RoomEvent]:
        return list(self._history)

    def _emit(self, event_type: EventType, sender: str, data: dict[str, Any]) -> RoomEvent:
        event = RoomEvent(type=event_type, sender=sender, data=data)
        self._history.append(event)
        logger.info("Room[%s] %s from %s", self.name, event_type.value, sender)
        for handler in self._handlers.get(event_type, []):
            handler(event)
        for handler in self._handlers.get("*", []):
            handler(event)
        return event

    def __repr__(self) -> str:
        return f"Room({self.name!r}, members={self.member_count})"
