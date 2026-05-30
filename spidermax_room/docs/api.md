# API Reference — MAX ROOM

## spidermax_room

```python
import spidermax_room
```

### Constants

| Name | Type | Value |
|------|------|-------|
| `__version__` | `str` | `"2.0.0"` |

## Workflow Registration

### `@spidermax_room.workflow.register(name)`

Decorator to register a function as a scheduled workflow task.

```python
@spidermax_room.workflow.register("daily_sync")
def daily_sync():
    ...
```

## EventBus

### `EventBus.publish(sender, topic, message)`

Publish a message to all subscribers.

### `EventBus.subscribe(topic, callback)`

Subscribe to messages matching a topic pattern.

### `EventBus.initialize()`

Initialize the singleton event bus instance.

## Scheduler

### `Scheduler.add_job(cron, func, args)`

Register a cron-based job.

### `Scheduler.start()`

Start the scheduler loop in a background thread.
