"""
RoomEngine — manages multiple collaboration rooms.

Creates, tracks, and routes events between rooms.
"""

from __future__ import annotations

import logging
from typing import Any

from .room import Room
from .member import Member
from .event import RoomEvent

logger = logging.getLogger(__name__)


class RoomEngine:
    """Manages a collection of collaboration rooms."""

    def __init__(self) -> None:
        self._rooms: dict[str, Room] = {}

    def create_room(self, name: str) -> Room:
        """Create a new collaboration room."""
        room = Room(name)
        self._rooms[name] = room
        logger.info("Room created: %s", name)
        return room

    def get_room(self, name: str) -> Room | None:
        return self._rooms.get(name)

    def destroy_room(self, name: str) -> bool:
        if name in self._rooms:
            del self._rooms[name]
            logger.info("Room destroyed: %s", name)
            return True
        return False

    @property
    def room_names(self) -> list[str]:
        return list(self._rooms.keys())

    @property
    def room_count(self) -> int:
        return len(self._rooms)

    def status(self) -> dict[str, Any]:
        return {
            "room_count": self.room_count,
            "rooms": {
                name: {"members": room.member_count}
                for name, room in self._rooms.items()
            },
        }
