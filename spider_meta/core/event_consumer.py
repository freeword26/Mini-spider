import asyncio
import uuid
import logging
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from spider_meta.core.event_bus import Event, EventBus, EventType, EventPriority, event_bus
from spider_meta.core.schemas import SubTask, TaskStatus

logger = logging.getLogger("spider_meta.consumer")


class InMemoryEventQueue:
    """
    Async in-memory event queue with priority ordering and backpressure.

    Supports:
    - Priority ordering (CRITICAL > HIGH > NORMAL > LOW)
    - Max size with configurable overflow strategy (drop_oldest / reject)
    - Blocking dequeue with timeout
    - Batch dequeue
    """

    def __init__(self, max_size: int = 10000, overflow_strategy: str = "drop_oldest"):
        self._queues: Dict[EventPriority, asyncio.Queue] = {
            p: asyncio.Queue() for p in EventPriority
        }
        self._max_size = max_size
        self._overflow_strategy = overflow_strategy
        self._total_enqueued = 0
        self._total_dequeued = 0
        self._total_dropped = 0

    @property
    def size(self) -> int:
        return sum(q.qsize() for q in self._queues.values())

    @property
    def is_full(self) -> bool:
        return self.size >= self._max_size

    async def enqueue(self, event: Event) -> bool:
        queue = self._queues[event.priority]
        if self.is_full:
            if self._overflow_strategy == "reject":
                logger.warning(f"Queue full, rejecting event {event.event_id}")
                self._total_dropped += 1
                return False
            else:
                for priority in reversed(list(EventPriority)):
                    q = self._queues[priority]
                    if not q.empty():
                        try:
                            q.get_nowait()
                            self._total_dropped += 1
                            break
                        except asyncio.QueueEmpty:
                            continue
        await queue.put(event)
        self._total_enqueued += 1
        return True

    async def dequeue(self, timeout: float = 1.0) -> Optional[Event]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for priority in reversed(list(EventPriority)):
                q = self._queues[priority]
                try:
                    event = q.get_nowait()
                    self._total_dequeued += 1
                    return event
                except asyncio.QueueEmpty:
                    continue
            await asyncio.sleep(0.01)
        return None

    async def dequeue_batch(self, max_count: int = 10, timeout: float = 0.5) -> List[Event]:
        events = []
        deadline = time.monotonic() + timeout
        while len(events) < max_count and time.monotonic() < deadline:
            event = await self.dequeue(timeout=0.05)
            if event:
                events.append(event)
            else:
                break
        return events

    def get_stats(self) -> Dict[str, Any]:
        return {
            "size": self.size,
            "max_size": self._max_size,
            "total_enqueued": self._total_enqueued,
            "total_dequeued": self._total_dequeued,
            "total_dropped": self._total_dropped,
            "by_priority": {
                p.name: self._queues[p].qsize() for p in EventPriority
            },
        }


class RedisEventQueue:
    """
    Redis Streams-backed event queue for production deployments.

    Falls back to InMemoryEventQueue when Redis is unavailable.
    """

    def __init__(self, redis_client=None, stream_key: str = "spider_meta_events", consumer_group: str = "meta_agent"):
        self._redis = redis_client
        self._stream_key = stream_key
        self._consumer_group = consumer_group
        self._fallback = InMemoryEventQueue()
        self._available = False

    async def enqueue(self, event: Event) -> bool:
        if not self._available:
            return await self._fallback.enqueue(event)
        try:
            data = event.to_json()
            self._redis.xadd(self._stream_key, {"data": data}, maxlen=10000)
            return True
        except Exception as e:
            logger.warning(f"Redis enqueue failed: {e}, using fallback")
            self._available = False
            return await self._fallback.enqueue(event)

    async def dequeue(self, timeout: float = 1.0) -> Optional[Event]:
        if not self._available:
            return await self._fallback.dequeue(timeout)
        try:
            result = self._redis.xreadgroup(
                self._consumer_group, "consumer-1",
                {self._stream_key: ">"},
                count=1,
                block=int(timeout * 1000),
            )
            if result:
                for stream, messages in result:
                    for msg_id, msg_data in messages:
                        event_data = msg_data.get("data", msg_data.get(b"data", b"{}"))
                        if isinstance(event_data, bytes):
                            event_data = event_data.decode("utf-8")
                        return Event.from_json(event_data)
            return None
        except Exception as e:
            logger.warning(f"Redis dequeue failed: {e}, using fallback")
            self._available = False
            return await self._fallback.dequeue(timeout)

    async def dequeue_batch(self, max_count: int = 10, timeout: float = 0.5) -> List[Event]:
        events = []
        deadline = time.monotonic() + timeout
        while len(events) < max_count and time.monotonic() < deadline:
            event = await self.dequeue(timeout=0.05)
            if event:
                events.append(event)
            else:
                break
        return events


class TaskAutoAssigner:
    """
    Auto-assigns tasks on TASK_SUBMITTED events using the existing
    PipelineOrchestrator + WorkerDispatcher pipeline.

    Features:
    - Automatic task decomposition on TASK_SUBMITTED events
    - Worker skill matching and load-balanced dispatch
    - SOP-based serial execution for DAG tasks
    - Async result tracking
    """

    def __init__(
        self,
        orchestrator_factory: Optional[Callable] = None,
        decomposer_factory: Optional[Callable] = None,
        dispatcher_factory: Optional[Callable] = None,
    ):
        self._orchestrator_factory = orchestrator_factory
        self._decomposer_factory = decomposer_factory
        self._dispatcher_factory = dispatcher_factory
        self._active_assignments: Dict[str, Dict[str, Any]] = {}
        self._completed_assignments: Dict[str, Dict[str, Any]] = {}
        self._assignment_count = 0
        self._success_count = 0
        self._failure_count = 0

    async def handle_task_submitted(self, event: Event) -> None:
        """Handle TASK_SUBMITTED event — decompose, dispatch, and track."""
        task = event.data.get("task", "")
        if not task:
            logger.warning(f"Ignoring TASK_SUBMITTED event with empty task: {event.event_id}")
            return

        assignment_id = f"assign-{uuid.uuid4().hex[:8]}"
        correlation_id = event.correlation_id or event.event_id

        self._active_assignments[assignment_id] = {
            "assignment_id": assignment_id,
            "task": task,
            "correlation_id": correlation_id,
            "status": "processing",
            "started_at": datetime.utcnow().isoformat(),
            "subtasks": 0,
            "completed": 0,
            "failed": 0,
        }
        self._assignment_count += 1

        logger.info(f"Auto-assigning task: {task[:80]} (assignment={assignment_id})")

        try:
            from spider_meta.core.pipeline_orchestrator import PipelineOrchestrator
            orchestrator = self._orchestrator_factory() if self._orchestrator_factory else PipelineOrchestrator()

            result = await orchestrator.execute(task)

            status = "completed" if result.status == TaskStatus.COMPLETED else "failed"
            self._active_assignments[assignment_id].update({
                "status": status,
                "finished_at": datetime.utcnow().isoformat(),
                "subtasks": len(result.tree.subtasks) if result.tree else 0,
                "completed": sum(1 for r in result.results.values() if r is not None),
                "failed": sum(1 for r in result.results.values() if r is None),
                "errors": result.errors,
            })

            if status == "completed":
                self._success_count += 1
            else:
                self._failure_count += 1

            completed_at = datetime.utcnow().isoformat()
            self._completed_assignments[assignment_id] = {
                **self._active_assignments[assignment_id],
                "completed_at": completed_at,
            }

            await event_bus.publish(Event(
                event_type=EventType.TASK_COMPLETED if status == "completed" else EventType.TASK_FAILED,
                source="task_auto_assigner",
                data={
                    "assignment_id": assignment_id,
                    "task": task[:200],
                    "status": status,
                    "subtasks": self._active_assignments[assignment_id]["subtasks"],
                },
                correlation_id=correlation_id,
                priority=EventPriority.HIGH if status == "failed" else EventPriority.NORMAL,
            ))

            if len(self._active_assignments) > 1000:
                self._cleanup_old_assignments()

        except Exception as e:
            logger.error(f"Auto-assign failed for {assignment_id}: {e}")
            self._failure_count += 1
            self._active_assignments[assignment_id].update({
                "status": "error",
                "finished_at": datetime.utcnow().isoformat(),
                "errors": [str(e)],
            })
            await event_bus.publish(Event(
                event_type=EventType.TASK_FAILED,
                source="task_auto_assigner",
                data={
                    "assignment_id": assignment_id,
                    "task": task[:200],
                    "error": str(e),
                },
                correlation_id=correlation_id,
                priority=EventPriority.CRITICAL,
            ))

    def _cleanup_old_assignments(self, keep: int = 500):
        if len(self._active_assignments) > keep + 200:
            sorted_ids = sorted(
                self._active_assignments.keys(),
                key=lambda k: self._active_assignments[k].get("started_at", ""),
            )
            for old_id in sorted_ids[:len(sorted_ids) - keep]:
                self._active_assignments.pop(old_id, None)

    def get_assignment(self, assignment_id: str) -> Optional[Dict]:
        return self._active_assignments.get(assignment_id) or self._completed_assignments.get(assignment_id)

    def get_active_assignments(self) -> List[Dict]:
        return [v for v in self._active_assignments.values() if v["status"] == "processing"]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_assignments": self._assignment_count,
            "success_count": self._success_count,
            "failure_count": self._failure_count,
            "active_count": sum(1 for v in self._active_assignments.values() if v["status"] == "processing"),
            "completed_count": len(self._completed_assignments),
        }

    def reset(self):
        self._active_assignments.clear()
        self._completed_assignments.clear()
        self._assignment_count = 0
        self._success_count = 0
        self._failure_count = 0


class EventConsumer:
    """
    Async event consumer that bridges the EventQueue → EventBus → TaskAutoAssigner.

    Runs as a background task during FastAPI lifespan.
    Supports graceful shutdown.
    """

    def __init__(
        self,
        queue: Optional[InMemoryEventQueue] = None,
        bus: Optional[EventBus] = None,
        auto_assigner: Optional[TaskAutoAssigner] = None,
        consumer_id: str = "consumer-1",
        poll_interval: float = 0.1,
        max_batch_size: int = 10,
    ):
        self._queue = queue or InMemoryEventQueue()
        self._bus = bus or event_bus
        self._auto_assigner = auto_assigner or TaskAutoAssigner()
        self._consumer_id = consumer_id
        self._poll_interval = poll_interval
        self._max_batch_size = max_batch_size
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._processed_count = 0
        self._error_count = 0

    @property
    def auto_assigner(self) -> TaskAutoAssigner:
        return self._auto_assigner

    async def start(self):
        """Start the background consumer loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._consume_loop())
        logger.info(f"EventConsumer {self._consumer_id} started")

    async def stop(self):
        """Gracefully stop the consumer."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info(f"EventConsumer {self._consumer_id} stopped (processed={self._processed_count})")

    async def _consume_loop(self):
        while self._running:
            try:
                events = await self._queue.dequeue_batch(
                    max_count=self._max_batch_size,
                    timeout=self._poll_interval,
                )
                for event in events:
                    try:
                        await self._bus.publish(event)
                        self._processed_count += 1
                    except Exception as e:
                        self._error_count += 1
                        logger.error(f"Consumer error processing event {event.event_id}: {e}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._error_count += 1
                logger.error(f"Consumer loop error: {e}")
                await asyncio.sleep(0.5)

    async def submit_task(self, task: str, correlation_id: Optional[str] = None, priority: EventPriority = EventPriority.NORMAL) -> str:
        """Submit a task for auto-assignment via the event system."""
        event = Event(
            event_type=EventType.TASK_SUBMITTED,
            source="api",
            data={"task": task},
            correlation_id=correlation_id,
            priority=priority,
        )
        await self._queue.enqueue(event)
        return event.event_id

    def get_stats(self) -> Dict[str, Any]:
        return {
            "consumer_id": self._consumer_id,
            "running": self._running,
            "processed_count": self._processed_count,
            "error_count": self._error_count,
            "queue_stats": self._queue.get_stats(),
            "assigner_stats": self._auto_assigner.get_stats(),
            "bus_stats": self._bus.get_stats(),
        }
