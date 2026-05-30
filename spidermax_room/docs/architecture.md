# Architecture — MAX ROOM

## System Overview

MAX ROOM implements a three-layer closed-loop unattended workflow system.

```
┌─────────────────────────────────────────────┐
│              EventBus (Pub/Sub)             │
│         project_scheduler → * (all)         │
├─────────────────────────────────────────────┤
│              Scheduler Layer                │
│   22 projects × 116 cron jobs              │
│   (queue_drain, health_check, self_healing, │
│    metric_refresh, route_sync, ...)         │
├─────────────────────────────────────────────┤
│              Execution Layer                │
│   Self-Healing Module | Monitoring Module   │
│   Dashboard | Notification Center           │
└─────────────────────────────────────────────┘
```

## Core Modules

| Module | File | Responsibility |
|--------|------|----------------|
| EventBus | `src/event_bus.py` | Publish/subscribe messaging |
| Scheduler | `src/scheduler.py` | Cron-based task scheduling |
| Self-Healing | `src/self_healing.py` | Auto-detect & recover failures |
| Monitoring | `src/monitoring.py` | Metrics collection & dashboard |
| Notification | `src/notification.py` | Alert delivery & queue drain |

## Integration

MAX ROOM is a **functional package** integrated via workflow registration/triggers:

```python
import spidermax_room

# Register custom workflow
@spidermax_room.workflow.register("my_task")
def my_task():
    pass
```

## Data Flow

1. Scheduler fires cron job → publishes EventBus message
2. EventBus routes to all subscribed handlers
3. Execution layer processes and updates monitoring
4. Self-healer diagnoses issues on 15-min interval
5. Dashboard refreshes metrics via P021 chart_update
