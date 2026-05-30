"""
Tests for spidermax_room.

Run: pytest tests/ -v
"""

import unittest

from spidermax_room import (
    Member, MemberRole, MemberStatus,
    Room, RoomEngine, RoomEvent, EventType,
)


class TestMember(unittest.TestCase):
    def test_create_member(self):
        m = Member("alice")
        self.assertEqual(m.name, "alice")
        self.assertEqual(m.role, MemberRole.PARTICIPANT)
        self.assertEqual(m.status, MemberStatus.ONLINE)

    def test_member_with_role(self):
        m = Member("bob", role=MemberRole.FACILITATOR, status=MemberStatus.AWAY)
        self.assertEqual(m.role, MemberRole.FACILITATOR)


class TestRoomEvent(unittest.TestCase):
    def test_create_event(self):
        e = RoomEvent(EventType.MESSAGE, "alice", {"content": "hello"})
        self.assertEqual(e.type, EventType.MESSAGE)
        self.assertEqual(e.sender, "alice")


class TestRoom(unittest.TestCase):
    def test_create_room(self):
        room = Room("test-room")
        self.assertEqual(room.name, "test-room")
        self.assertEqual(room.member_count, 0)

    def test_join_and_leave(self):
        room = Room("test")
        room.join(Member("alice"))
        self.assertEqual(room.member_count, 1)
        room.leave("alice")
        self.assertEqual(room.member_count, 0)

    def test_join_emits_event(self):
        room = Room("test")
        events = []
        room.on_event(lambda e: events.append(e))
        room.join(Member("alice"))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].type, EventType.MEMBER_JOINED)

    def test_broadcast(self):
        room = Room("test")
        room.join(Member("alice"))
        room.join(Member("bob"))
        event = room.broadcast("alice", {"content": "hello"})
        self.assertIsNotNone(event)
        self.assertEqual(event.type, EventType.MESSAGE)

    def test_broadcast_by_nonmember_fails(self):
        room = Room("test")
        self.assertIsNone(room.broadcast("stranger", {}))

    def test_send_to(self):
        room = Room("test")
        room.join(Member("alice"))
        room.join(Member("bob"))
        event = room.send_to("alice", "bob", {"content": "hi"})
        self.assertIsNotNone(event)
        self.assertEqual(event.data["recipient"], "bob")

    def test_status_change(self):
        room = Room("test")
        room.join(Member("alice"))
        event = room.set_status("alice", MemberStatus.AWAY)
        self.assertIsNotNone(event)
        self.assertEqual(event.type, EventType.MEMBER_STATUS_CHANGED)
        self.assertEqual(room.get_member("alice").status, MemberStatus.AWAY)

    def test_history(self):
        room = Room("test")
        room.join(Member("alice"))
        room.broadcast("alice", {"content": "hi"})
        room.leave("alice")
        self.assertEqual(len(room.history), 3)

    def test_leave_nonmember_returns_none(self):
        room = Room("test")
        self.assertIsNone(room.leave("nobody"))


class TestRoomEngine(unittest.TestCase):
    def test_create_and_get(self):
        engine = RoomEngine()
        room = engine.create_room("standup")
        self.assertEqual(room.name, "standup")
        self.assertIs(engine.get_room("standup"), room)

    def test_destroy_room(self):
        engine = RoomEngine()
        engine.create_room("temp")
        self.assertTrue(engine.destroy_room("temp"))
        self.assertIsNone(engine.get_room("temp"))

    def test_destroy_nonexistent(self):
        engine = RoomEngine()
        self.assertFalse(engine.destroy_room("ghost"))

    def test_room_count(self):
        engine = RoomEngine()
        engine.create_room("a")
        engine.create_room("b")
        self.assertEqual(engine.room_count, 2)

    def test_full_scenario(self):
        engine = RoomEngine()
        room = engine.create_room("sprint-planning")

        room.join(Member("pm", role=MemberRole.FACILITATOR))
        room.join(Member("dev-1", role=MemberRole.PARTICIPANT))
        room.join(Member("dev-2", role=MemberRole.PARTICIPANT))

        events = []
        room.on_event(lambda e: events.append(e))

        room.broadcast("pm", {"content": "Sprint planning starts"})
        room.send_to("dev-1", "dev-2", {"content": "I'll take ticket-101"})
        room.set_status("dev-2", MemberStatus.AWAY)

        self.assertEqual(len(events), 3)
        self.assertEqual(events[0].type, EventType.MESSAGE)
        self.assertEqual(events[2].type, EventType.MEMBER_STATUS_CHANGED)
        self.assertEqual(room.member_count, 3)

        engine.destroy_room("sprint-planning")
        self.assertEqual(engine.room_count, 0)


if __name__ == "__main__":
    unittest.main()
