"""
Room Member — a participant in a collaboration room.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class MemberRole(Enum):
    FACILITATOR = "facilitor"
    PARTICIPANT = "participant"
    OBSERVER = "observer"


class MemberStatus(Enum):
    ONLINE = "online"
    AWAY = "away"
    OFFLINE = "offline"


@dataclass
class Member:
    name: str
    role: MemberRole = MemberRole.PARTICIPANT
    status: MemberStatus = MemberStatus.ONLINE
    metadata: dict = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"Member({self.name}, role={self.role.value}, status={self.status.value})"
