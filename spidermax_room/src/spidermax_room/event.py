"""
Room Event — events that happen inside a collaboration room.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EventType(Enum):
    MEMBER_JOINED = "member_joined"
    MEMBER_LEFT = "member_left"
    MEMBER_STATUS_CHANGED = "member_status_changed"
    MESSAGE = "message"
    WHITEBOARD_UPDATE = "whiteboard_update"
    DOCUMENT_SHARED = "document_shared"
    TASK_UPDATED = "task_updated"
    CUSTOM = "custom"


@dataclass
class RoomEvent:
    type: EventType
    sender: str
    data: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"RoomEvent({self.type.value}, sender={self.sender})"
