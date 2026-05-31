import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

from spider_meta.core.event_bus import Event, EventBus, EventType, EventPriority, event_bus
from spider_meta.core.event_consumer import InMemoryEventQueue, TaskAutoAssigner, EventConsumer


# ─────────────────────────────────────────────────────────────────────────
# Event Tests
# ─────────────────────────────────────────────────────────────────────────

class TestEvent:
    def test_create_event(self):
        event = Event(
            event_type=EventType.TASK_SUBMITTED,
            source="test",
            data={"task": "do something"},
        )
        assert event.event_type == EventType.TASK_SUBMITTED
        assert event.source == "test"
        assert event.data["task"] == "do something"
        assert event.event_id.startswith("evt-")
        assert event.priority == EventPriority.NORMAL

    def test_event_to_dict_roundtrip(self):
        event = Event(
            event_type=EventType.TASK_COMPLETED,
            source="worker-1",
            data={"result": "ok"},
            priority=EventPriority.HIGH,
        )
        d = event.to_dict()
        restored = Event.from_dict(d)
        assert restored.event_type == event.event_type
        assert restored.source == event.source
        assert restored.data == event.data
        assert restored.priority == event.priority

    def test_event_to_json_roundtrip(self):
        event = Event(
            event_type=EventType.WORKER_HEARTBEAT,
            source="worker-1",
            data={"load": 0.5},
        )
        json_str = event.to_json()
        restored = Event.from_json(json_str)
        assert restored.event_type == event.event_type
        assert restored.data["load"] == 0.5

    def test_event_priority_values(self):
        assert EventPriority.LOW.value == 0
        assert EventPriority.NORMAL.value == 1
        assert EventPriority.HIGH.value == 2
        assert EventPriority.CRITICAL.value == 3

    def test_event_correlation_id(self):
        event = Event(
            event_type=EventType.TASK_SUBMITTED,
            source="test",
            data={},
            correlation_id="corr-123",
        )
        assert event.correlation_id == "corr-123"

    def test_all_event_types(self):
        for et in EventType:
            assert isinstance(et.value, str)
            assert "." in et.value


# ─────────────────────────────────────────────────────────────────────────
# EventBus Tests (all async via pytest-asyncio)
# ─────────────────────────────────────────────────────────────────────────

class TestEventBus:
    @pytest.fixture(autouse=True)
    def _reset_bus(self):
        event_bus.reset()
        yield
        event_bus.reset()

    @pytest.mark.asyncio
    async def test_subscribe_and_publish(self):
        received = []

        def handler(event):
            received.append(event)

        event_bus.subscribe([EventType.TASK_SUBMITTED], handler)
        event = Event(EventType.TASK_SUBMITTED, "test", {"task": "hello"})
        await event_bus.publish(event)
        assert len(received) == 1
        assert received[0].data["task"] == "hello"

    @pytest.mark.asyncio
    async def test_async_handler(self):
        received = []

        async def handler(event):
            received.append(event)

        event_bus.subscribe([EventType.TASK_SUBMITTED], handler)
        event = Event(EventType.TASK_SUBMITTED, "test", {"task": "async_task"})
        await event_bus.publish(event)
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_subscribe_multiple_event_types(self):
        received = []

        def handler(event):
            received.append(event.event_type)

        event_bus.subscribe(
            [EventType.TASK_SUBMITTED, EventType.TASK_COMPLETED],
            handler,
        )
        await event_bus.publish(Event(EventType.TASK_SUBMITTED, "t", {}))
        await event_bus.publish(Event(EventType.TASK_COMPLETED, "t", {}))
        await event_bus.publish(Event(EventType.TASK_FAILED, "t", {}))
        assert len(received) == 2
        assert EventType.TASK_SUBMITTED in received
        assert EventType.TASK_COMPLETED in received

    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        received = []

        def handler(event):
            received.append(event)

        sub_id = event_bus.subscribe([EventType.TASK_SUBMITTED], handler)
        event_bus.unsubscribe(sub_id)
        event = Event(EventType.TASK_SUBMITTED, "test", {})
        await event_bus.publish(event)
        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_filter_function(self):
        received = []

        def handler(event):
            received.append(event)

        def only_high_load(event):
            return event.data.get("load", 0) > 0.8

        event_bus.subscribe(
            [EventType.WORKER_HEARTBEAT],
            handler,
            filter_fn=only_high_load,
        )
        await event_bus.publish(Event(EventType.WORKER_HEARTBEAT, "w", {"load": 0.5}))
        await event_bus.publish(Event(EventType.WORKER_HEARTBEAT, "w", {"load": 0.9}))
        assert len(received) == 1
        assert received[0].data["load"] == 0.9

    @pytest.mark.asyncio
    async def test_event_history(self):
        for i in range(5):
            await event_bus.publish(Event(EventType.TASK_SUBMITTED, "t", {"i": i}))
        history = event_bus.get_history(limit=3)
        assert len(history) == 3
        assert history[-1].data["i"] == 4

    @pytest.mark.asyncio
    async def test_event_history_filtered(self):
        await event_bus.publish(Event(EventType.TASK_SUBMITTED, "t", {}))
        await event_bus.publish(Event(EventType.TASK_COMPLETED, "t", {}))
        history = event_bus.get_history(event_type=EventType.TASK_SUBMITTED)
        assert len(history) == 1

    @pytest.mark.asyncio
    async def test_event_stats(self):
        await event_bus.publish(Event(EventType.TASK_SUBMITTED, "t", {}))
        await event_bus.publish(Event(EventType.TASK_SUBMITTED, "t", {}))
        await event_bus.publish(Event(EventType.TASK_COMPLETED, "t", {}))
        stats = event_bus.get_stats()
        assert stats["total_published"] == 3
        assert stats["event_counts"]["task.submitted"] == 2

    @pytest.mark.asyncio
    async def test_publish_count_return(self):
        def handler(event):
            pass

        event_bus.subscribe([EventType.TASK_SUBMITTED], handler)
        event = Event(EventType.TASK_SUBMITTED, "test", {})
        count = await event_bus.publish(event)
        assert count >= 1

    @pytest.mark.asyncio
    async def test_subscriber_priority(self):
        order = []

        def handler_low(event):
            order.append("low")

        def handler_high(event):
            order.append("high")

        event_bus.subscribe([EventType.TASK_SUBMITTED], handler_low, priority=0)
        event_bus.subscribe([EventType.TASK_SUBMITTED], handler_high, priority=10)
        event = Event(EventType.TASK_SUBMITTED, "test", {})
        await event_bus.publish(event)
        assert order[0] == "high"
        assert order[1] == "low"

    @pytest.mark.asyncio
    async def test_handler_error_isolated(self):
        good_received = []

        def bad_handler(event):
            raise RuntimeError("boom")

        def good_handler(event):
            good_received.append(event)

        event_bus.subscribe([EventType.TASK_SUBMITTED], bad_handler)
        event_bus.subscribe([EventType.TASK_SUBMITTED], good_handler)
        event = Event(EventType.TASK_SUBMITTED, "test", {})
        await event_bus.publish(event)
        assert len(good_received) == 1


# ─────────────────────────────────────────────────────────────────────────
# InMemoryEventQueue Tests
# ─────────────────────────────────────────────────────────────────────────

class TestInMemoryEventQueue:
    @pytest.mark.asyncio
    async def test_enqueue_dequeue(self):
        q = InMemoryEventQueue()
        event = Event(EventType.TASK_SUBMITTED, "test", {"task": "x"})
        assert await q.enqueue(event)
        dequeued = await q.dequeue(timeout=0.5)
        assert dequeued is not None
        assert dequeued.event_id == event.event_id

    @pytest.mark.asyncio
    async def test_priority_ordering(self):
        q = InMemoryEventQueue()
        low = Event(EventType.TASK_SUBMITTED, "t", {"p": "low"}, priority=EventPriority.LOW)
        high = Event(EventType.TASK_SUBMITTED, "t", {"p": "high"}, priority=EventPriority.HIGH)
        await q.enqueue(low)
        await q.enqueue(high)
        first = await q.dequeue(timeout=0.5)
        assert first.data["p"] == "high"

    @pytest.mark.asyncio
    async def test_dequeue_timeout(self):
        q = InMemoryEventQueue()
        result = await q.dequeue(timeout=0.1)
        assert result is None

    @pytest.mark.asyncio
    async def test_dequeue_batch(self):
        q = InMemoryEventQueue()
        for i in range(5):
            await q.enqueue(Event(EventType.TASK_SUBMITTED, "t", {"i": i}))
        batch = await q.dequeue_batch(max_count=3, timeout=0.5)
        assert len(batch) == 3

    @pytest.mark.asyncio
    async def test_overflow_drop_oldest(self):
        q = InMemoryEventQueue(max_size=3)
        for i in range(5):
            await q.enqueue(Event(EventType.TASK_SUBMITTED, "t", {"i": i}))
        assert q.size == 3
        stats = q.get_stats()
        assert stats["total_dropped"] == 2

    @pytest.mark.asyncio
    async def test_overflow_reject(self):
        q = InMemoryEventQueue(max_size=2, overflow_strategy="reject")
        assert await q.enqueue(Event(EventType.TASK_SUBMITTED, "t", {"i": 0}))
        assert await q.enqueue(Event(EventType.TASK_SUBMITTED, "t", {"i": 1}))
        result = await q.enqueue(Event(EventType.TASK_SUBMITTED, "t", {"i": 2}))
        assert result is False

    @pytest.mark.asyncio
    async def test_stats(self):
        q = InMemoryEventQueue()
        await q.enqueue(Event(EventType.TASK_SUBMITTED, "t", {}))
        await q.dequeue(timeout=0.5)
        stats = q.get_stats()
        assert stats["total_enqueued"] == 1
        assert stats["total_dequeued"] == 1
        assert stats["size"] == 0


# ─────────────────────────────────────────────────────────────────────────
# TaskAutoAssigner Tests
# ─────────────────────────────────────────────────────────────────────────

class MockSettings:
    redis_host = "localhost"
    redis_port = 6381
    redis_db = 0
    debug = False
    llm_model = "test"
    llm_max_tokens = 1024
    llm_api_url = ""
    llm_api_key = ""
    kg_collection_name = "test"
    kg_top_k = 3
    enable_knowledge_retrieval = False
    kg_cache_size = 10
    kg_retrieval_timeout = 1.0
    enable_experience_reuse = False
    experience_top_k = 3
    default_parallelism = 3
    min_parallelism = 1
    max_parallelism = 10
    worker_heartbeat_timeout = 3600
    worker_max_tasks = 5


class TestTaskAutoAssigner:
    @pytest.fixture(autouse=True)
    def _reset_bus(self):
        event_bus.reset()
        yield
        event_bus.reset()

    @pytest.mark.asyncio
    async def test_handle_empty_task(self):
        assigner = TaskAutoAssigner()
        event = Event(EventType.TASK_SUBMITTED, "test", {"task": ""})
        await assigner.handle_task_submitted(event)
        assert assigner._assignment_count == 0

    @pytest.mark.asyncio
    async def test_handle_task_submitted(self):
        with patch("spider_meta.config.load_settings", return_value=MockSettings()):
            with patch("spider_meta.core.pipeline_orchestrator.load_settings", return_value=MockSettings()):
                with patch("spider_meta.core.worker_dispatcher.load_settings", return_value=MockSettings()):
                    assigner = TaskAutoAssigner()
                    event = Event(
                        EventType.TASK_SUBMITTED, "test",
                        {"task": "Analyze data"},
                        correlation_id="corr-1",
                    )
                    await assigner.handle_task_submitted(event)
                    assert assigner._assignment_count == 1
                    assert assigner._success_count == 1

    @pytest.mark.asyncio
    async def test_assignment_tracking(self):
        with patch("spider_meta.config.load_settings", return_value=MockSettings()):
            with patch("spider_meta.core.pipeline_orchestrator.load_settings", return_value=MockSettings()):
                with patch("spider_meta.core.worker_dispatcher.load_settings", return_value=MockSettings()):
                    assigner = TaskAutoAssigner()
                    event = Event(EventType.TASK_SUBMITTED, "test", {"task": "Build API"})
                    await assigner.handle_task_submitted(event)
                    stats = assigner.get_stats()
                    assert stats["total_assignments"] == 1
                    assert stats["success_count"] == 1

    @pytest.mark.asyncio
    async def test_multiple_tasks(self):
        with patch("spider_meta.config.load_settings", return_value=MockSettings()):
            with patch("spider_meta.core.pipeline_orchestrator.load_settings", return_value=MockSettings()):
                with patch("spider_meta.core.worker_dispatcher.load_settings", return_value=MockSettings()):
                    assigner = TaskAutoAssigner()
                    for i in range(3):
                        event = Event(EventType.TASK_SUBMITTED, "test", {"task": f"Task {i}"})
                        await assigner.handle_task_submitted(event)
                    stats = assigner.get_stats()
                    assert stats["total_assignments"] == 3

    def test_get_assignment(self):
        assigner = TaskAutoAssigner()
        assigner._active_assignments["a1"] = {"status": "processing"}
        assert assigner.get_assignment("a1") is not None
        assert assigner.get_assignment("nonexistent") is None

    def test_get_active_assignments(self):
        assigner = TaskAutoAssigner()
        assigner._active_assignments["a1"] = {"status": "processing"}
        assigner._active_assignments["a2"] = {"status": "completed"}
        active = assigner.get_active_assignments()
        assert len(active) == 1

    def test_reset(self):
        assigner = TaskAutoAssigner()
        assigner._assignment_count = 10
        assigner.reset()
        assert assigner._assignment_count == 0


# ─────────────────────────────────────────────────────────────────────────
# EventConsumer Tests
# ─────────────────────────────────────────────────────────────────────────

class TestEventConsumer:
    @pytest.fixture(autouse=True)
    def _reset_bus(self):
        event_bus.reset()
        yield
        event_bus.reset()

    @pytest.mark.asyncio
    async def test_start_stop(self):
        consumer = EventConsumer(poll_interval=0.05)
        await consumer.start()
        assert consumer._running is True
        await consumer.stop()
        assert consumer._running is False

    @pytest.mark.asyncio
    async def test_submit_task(self):
        consumer = EventConsumer()
        event_id = await consumer.submit_task("Test task")
        assert event_id.startswith("evt-")
        assert consumer._queue.size == 1

    @pytest.mark.asyncio
    async def test_consume_and_publish(self):
        consumer = EventConsumer(poll_interval=0.05)
        bus_received = []

        async def handler(event):
            bus_received.append(event)

        event_bus.subscribe([EventType.TASK_SUBMITTED], handler)
        await consumer.start()
        await consumer.submit_task("Hello")
        await asyncio.sleep(0.3)
        await consumer.stop()
        assert len(bus_received) >= 1

    @pytest.mark.asyncio
    async def test_stats(self):
        consumer = EventConsumer()
        stats = consumer.get_stats()
        assert "consumer_id" in stats
        assert "queue_stats" in stats
        assert "assigner_stats" in stats
        assert "bus_stats" in stats

    @pytest.mark.asyncio
    async def test_double_start(self):
        consumer = EventConsumer(poll_interval=0.05)
        await consumer.start()
        await consumer.start()
        assert consumer._running is True
        await consumer.stop()

    @pytest.mark.asyncio
    async def test_submit_with_priority(self):
        consumer = EventConsumer()
        await consumer.submit_task("Critical", priority=EventPriority.CRITICAL)
        await consumer.submit_task("Low", priority=EventPriority.LOW)
        assert consumer._queue.size == 2
