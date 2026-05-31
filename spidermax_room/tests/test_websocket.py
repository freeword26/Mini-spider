"""
Integration tests for WebSocket layer (v2.1).
Run: pytest tests/test_websocket.py -v
"""

import asyncio
import json
import unittest

from spidermax_room import RoomSocketServer, RoomClient, Member, MemberRole
from spidermax_room.client import ServerMessage


def _next_port() -> int:
    _next_port._counter += 1
    return 20000 + _next_port._counter
_next_port._counter = 0


class TestWebSocketServer(unittest.TestCase):

    def test_create(self):
        s = RoomSocketServer(host="127.0.0.1", port=29999)
        self.assertEqual(s.port, 29999)

    def test_get_or_create_room(self):
        s = RoomSocketServer(host="127.0.0.1", port=29999)
        r = s.get_or_create_room("r")
        self.assertIs(r, s.get_or_create_room("r"))

    def test_get_room_none(self):
        s = RoomSocketServer(host="127.0.0.1", port=29999)
        self.assertIsNone(s.get_room("ghost"))


class TestWebSocketIntegration(unittest.TestCase):

    def _run(self, coro):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    def test_join_ack(self):
        """Join room returns ack with action=join."""
        port = _next_port()
        server = RoomSocketServer(host="127.0.0.1", port=port)
        base = f"ws://127.0.0.1:{port}"

        async def _test():
            import uvicorn
            cfg = uvicorn.Config(app=server.app, host="127.0.0.1", port=port, log_level="warning")
            srv = uvicorn.Server(cfg)
            task = asyncio.create_task(srv.serve())
            await asyncio.sleep(0.3)
            try:
                async with RoomClient(f"{base}/ws/alice") as alice:
                    ack = await alice.join("room1", Member("alice"))
                    self.assertEqual(ack["action"], "join")
            finally:
                srv.should_exit = True
                await asyncio.sleep(0.2)

        self._run(_test())

    def test_join_and_broadcast(self):
        """Alice broadcasts; Bob receives the message event."""
        port = _next_port()
        server = RoomSocketServer(host="127.0.0.1", port=port)
        base = f"ws://127.0.0.1:{port}"

        async def _test():
            import uvicorn
            cfg = uvicorn.Config(app=server.app, host="127.0.0.1", port=port, log_level="warning")
            srv = uvicorn.Server(cfg)
            task = asyncio.create_task(srv.serve())
            await asyncio.sleep(0.3)
            try:
                async with RoomClient(f"{base}/ws/alice") as alice:
                    await alice.join("room1", Member("alice"))
                    async with RoomClient(f"{base}/ws/bob") as bob:
                        await bob.join("room1", Member("bob"))
                        await asyncio.sleep(0.2)
                        await alice.broadcast("room1", {"content": "hello"})
                        await asyncio.sleep(0.3)
                        events = await bob.receive_events(count=10, timeout=3.0)
                        senders = [e.data.get("event", {}).get("sender") for e in events]
                        self.assertIn("alice", senders)
            finally:
                srv.should_exit = True
                await asyncio.sleep(0.2)

        self._run(_test())

    def test_send_to(self):
        """Alice sends direct message to Bob."""
        port = _next_port()
        server = RoomSocketServer(host="127.0.0.1", port=port)
        base = f"ws://127.0.0.1:{port}"

        async def _test():
            import uvicorn
            cfg = uvicorn.Config(app=server.app, host="127.0.0.1", port=port, log_level="warning")
            srv = uvicorn.Server(cfg)
            task = asyncio.create_task(srv.serve())
            await asyncio.sleep(0.3)
            try:
                async with RoomClient(f"{base}/ws/alice") as alice:
                    await alice.join("dm", Member("alice"))
                    async with RoomClient(f"{base}/ws/bob") as bob:
                        await bob.join("dm", Member("bob"))
                        await asyncio.sleep(0.2)
                        await alice.send_to("dm", "bob", {"content": "priv"})
                        await asyncio.sleep(0.3)
                        events = await bob.receive_events(count=10, timeout=3.0)
                        self.assertTrue(len(events) > 0)
                        senders = [e.data.get("event", {}).get("sender") for e in events]
                        self.assertIn("alice", senders)
            finally:
                srv.should_exit = True
                await asyncio.sleep(0.2)

        self._run(_test())

    def test_leave(self):
        """Join then leave, get leave ack."""
        port = _next_port()
        server = RoomSocketServer(host="127.0.0.1", port=port)
        base = f"ws://127.0.0.1:{port}"

        async def _test():
            import uvicorn
            cfg = uvicorn.Config(app=server.app, host="127.0.0.1", port=port, log_level="warning")
            srv = uvicorn.Server(cfg)
            task = asyncio.create_task(srv.serve())
            await asyncio.sleep(0.3)
            try:
                async with RoomClient(f"{base}/ws/alice") as alice:
                    ack = await alice.join("lr", Member("alice"))
                    self.assertEqual(ack["action"], "join")
                    ack = await alice.leave("lr")
                    self.assertEqual(ack["action"], "leave")
            finally:
                srv.should_exit = True
                await asyncio.sleep(0.2)

        self._run(_test())

    def test_list_rooms(self):
        """List rooms returns created room."""
        port = _next_port()
        server = RoomSocketServer(host="127.0.0.1", port=port)
        base = f"ws://127.0.0.1:{port}"

        async def _test():
            import uvicorn
            cfg = uvicorn.Config(app=server.app, host="127.0.0.1", port=port, log_level="warning")
            srv = uvicorn.Server(cfg)
            task = asyncio.create_task(srv.serve())
            await asyncio.sleep(0.3)
            try:
                async with RoomClient(f"{base}/ws/alice") as alice:
                    await alice.join("z-room", Member("alice"))
                    rooms = await alice.list_rooms()
                    names = [r["name"] for r in rooms]
                    self.assertIn("z-room", names)
            finally:
                srv.should_exit = True
                await asyncio.sleep(0.2)

        self._run(_test())

    def test_three_member_broadcast(self):
        """3 members, broadcast reaches all. Uses separate connections sequentially."""
        port = _next_port()
        server = RoomSocketServer(host="127.0.0.1", port=port)
        base = f"ws://127.0.0.1:{port}"

        async def _test():
            import uvicorn
            cfg = uvicorn.Config(app=server.app, host="127.0.0.1", port=port, log_level="warning")
            srv = uvicorn.Server(cfg)
            task = asyncio.create_task(srv.serve())
            await asyncio.sleep(0.3)
            try:
                # Alice joins
                async with RoomClient(f"{base}/ws/alice") as alice:
                    await alice.join("standup", Member("alice", role=MemberRole.FACILITATOR))
                    # Bob joins
                    async with RoomClient(f"{base}/ws/bob") as bob:
                        await bob.join("standup", Member("bob"))
                        # Carol joins
                        async with RoomClient(f"{base}/ws/carol") as carol:
                            await carol.join("standup", Member("carol"))
                            await asyncio.sleep(0.5)  # Wait for join events to settle
                            # Drain join events
                            await bob.receive_events(count=20, timeout=2.0)
                            await carol.receive_events(count=20, timeout=2.0)
                            # Broadcast
                            await alice.broadcast("standup", {"content": "meeting!"})
                            await asyncio.sleep(0.5)
                            bob_events = await bob.receive_events(count=10, timeout=3.0)
                            carol_events = await carol.receive_events(count=10, timeout=3.0)
                            bob_senders = [e.data.get("event", {}).get("sender") for e in bob_events]
                            carol_senders = [e.data.get("event", {}).get("sender") for e in carol_events]
                            self.assertIn("alice", bob_senders)
                            self.assertIn("alice", carol_senders)
            finally:
                srv.should_exit = True
                await asyncio.sleep(0.2)

        self._run(_test())


class TestRoomClient(unittest.TestCase):

    def test_creation(self):
        c = RoomClient("ws://x/ws/y")
        self.assertFalse(c.connected)

    def test_message_parsing(self):
        m = ServerMessage.from_json('{"type":"event","event":{"t":"m"}}')
        self.assertEqual(m.type, "event")


if __name__ == "__main__":
    unittest.main()
