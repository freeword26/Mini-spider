import uuid
import json
import time
import asyncio
import logging
import inspect
from enum import Enum
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field

logger = logging.getLogger("spider_meta.events")


class EventType(str, Enum):
    """All event types in the Spider-Meta event system."""

    # Task lifecycle events
    TASK_SUBMITTED = "task.submitted"
    TASK_DECOMPOSED = "task.decomposed"
    TASK_ASSIGNED = "task.assigned"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"

    # Subtask events
    SUBTASK_CREATED = "subtask.created"
    SUBTASK_DISPATCHED = "subtask.dispatched"
    SUBTASK_COMPLETED = "subtask.completed"
    SUBTASK_FAILED = "subtask.failed"

    # Worker events
    WORKER_REGISTERED = "worker.registered"
    WORKER_UNREGISTERED = "worker.unregistered"
    WORKER_HEARTBEAT = "worker.heartbeat"
    WORKER_OVERLOADED = "worker.overloaded"

    # Pipeline events
    PIPELINE_CREATED = "pipeline.created"
    PIPELINE_PHASE_CHANGED = "pipeline.phase_changed"
    PIPELINE_COMPLETED = "pipeline.completed"
    PIPELINE_FAILED = "pipeline.failed"

    # DAG events
    DAG_BUILT = "dag.built"
    DAG_LAYER_STARTED = "dag.layer.started"
    DAG_LAYER_COMPLETED = "dag.layer.completed"
    DAG_EXECUTION_STARTED = "dag.execution.started"
    DAG_EXECUTION_COMPLETED = "dag.execution.completed"

    # System events
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    CONFIG_CHANGED = "config.changed"


class EventPriority(int, Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


def _default_event_id():
    return f"evt-{uuid.uuid4().hex[:8]}"


def _default_timestamp():
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Event:
    """Immutable event object flowing through the event bus."""
    event_type: EventType
    source: str
    data: Dict[str, Any]
    event_id: str = field(default_factory=_default_event_id)
    timestamp: str = field(default_factory=_default_timestamp)
    priority: EventPriority = EventPriority.NORMAL
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "source": self.source,
            "data": self.data,
            "timestamp": self.timestamp,
            "priority": self.priority.value,
            "correlation_id": self.correlation_id,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Event":
        return cls(
            event_type=EventType(d["event_type"]),
            source=d["source"],
            data=d["data"],
            event_id=d.get("event_id", f"evt-{uuid.uuid4().hex[:8]}"),
            timestamp=d.get("timestamp", datetime.now(timezone.utc).isoformat()),
            priority=EventPriority(d.get("priority", 1)),
            correlation_id=d.get("correlation_id"),
            metadata=d.get("metadata", {}),
        )

    @classmethod
    def from_json(cls, s: str) -> "Event":
        return cls.from_dict(json.loads(s))


@dataclass
class EventSubscription:
    """A subscriber's registration on the event bus."""
    subscription_id: str
    event_types: Set[EventType]
    handler: Callable
    filter_fn: Optional[Callable[[Event], bool]] = None
    priority: int = 0


class EventBus:
    """
    In-memory async event bus with pub/sub semantics.

    Supports:
    - Subscribe to event types with optional filter
    - Publish events to all matching subscribers
    - Event history with configurable retention
    - Subscriber priority ordering
    """

    def __init__(self, history_size: int = 1000):
        self._subscribers: Dict[str, EventSubscription] = {}
        self._event_history: List[Event] = []
        self._history_size = history_size
        self._event_counts: Dict[str, int] = {}
        self._total_published = 0

    def subscribe(
        self,
        event_types: List[EventType],
        handler: Callable,
        filter_fn: Optional[Callable[[Event], bool]] = None,
        subscription_id: Optional[str] = None,
        priority: int = 0,
    ) -> str:
        sub_id = subscription_id or f"sub-{uuid.uuid4().hex[:8]}"
        self._subscribers[sub_id] = EventSubscription(
            subscription_id=sub_id,
            event_types=set(event_types),
            handler=handler,
            filter_fn=filter_fn,
            priority=priority,
        )
        logger.debug(f"EventBus: subscriber {sub_id} registered for {[e.value for e in event_types]}")
        return sub_id

    def unsubscribe(self, subscription_id: str) -> bool:
        if subscription_id in self._subscribers:
            del self._subscribers[subscription_id]
            logger.debug(f"EventBus: subscriber {subscription_id} removed")
            return True
        return False

    async def publish(self, event: Event) -> int:
        """Publish event to all matching subscribers. Returns count of notified subscribers."""
        self._event_history.append(event)
        if len(self._event_history) > self._history_size:
            self._event_history = self._event_history[-self._history_size:]

        self._total_published += 1
        self._event_counts[event.event_type.value] = self._event_counts.get(event.event_type.value, 0) + 1

        notified = 0
        sorted_subs = sorted(self._subscribers.values(), key=lambda s: s.priority, reverse=True)

        for sub in sorted_subs:
            if event.event_type not in sub.event_types:
                continue
            if sub.filter_fn and not sub.filter_fn(event):
                continue
            try:
                if inspect.iscoroutinefunction(sub.handler):
                    await sub.handler(event)
                else:
                    sub.handler(event)
                notified += 1
            except Exception as e:
                logger.error(f"EventBus: handler error for sub {sub.subscription_id}: {e}")

        logger.debug(f"EventBus: published {event.event_type.value} -> {notified} subscribers")
        return notified

    def get_history(
        self,
        event_type: Optional[EventType] = None,
        limit: int = 100,
        since: Optional[str] = None,
    ) -> List[Event]:
        events = self._event_history
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if since:
            events = [e for e in events if e.timestamp >= since]
        return events[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_published": self._total_published,
            "subscriber_count": len(self._subscribers),
            "history_size": len(self._event_history),
            "history_capacity": self._history_size,
            "event_counts": dict(self._event_counts),
        }

    def clear_history(self):
        self._event_history.clear()

    def reset(self):
        self._event_history.clear()
        self._event_counts.clear()
        self._total_published = 0


# Global event bus instance
event_bus = EventBus()
