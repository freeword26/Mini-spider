# spider_meta API Reference

## Health Check

### `GET /health`

```json
{
    "status": "ok",
    "service": "meta-agent",
    "model": "gpt-4o-mini",
    "tools_count": 6,
    "active_sessions": 0
}
```

### `GET /health/detailed`

```json
{
    "status": "ok",
    "service": "meta-agent",
    "modules": {
        "pipeline": "available",
        "dag": "available",
        "knowledge": "available",
        "experience": "available"
    }
}
```

## Task Execution

### `POST /agent/run`

**Request:**
```json
{
    "task": "Analyze user behavior data and generate report",
    "max_steps": 20
}
```

**Response:**
```json
{
    "session_id": "session-a1b2c3d4",
    "task": "Analyze user behavior data and generate report",
    "steps_taken": 3,
    "finished": true,
    "result": "Task completed with observations: ...",
    "duration": "0:00:01.234"
}
```

### `POST /agent/plan`

**Request:**
```json
{
    "objective": "Build a user login system",
    "constraints": ["Must support OAuth", "Response time < 200ms"]
}
```

## Pipeline Execution

### `POST /pipeline/execute`

**Request:**
```json
{
    "task": "开发一个用户登录系统",
    "use_knowledge": true,
    "use_experience": true
}
```

**Response:**
```json
{
    "pipeline_id": "pipeline-x1y2z3",
    "status": "completed",
    "subtasks_count": 4,
    "completed_count": 4,
    "failed_count": 0,
    "errors": []
}
```

### `GET /pipeline/status/{pipeline_id}`

**Response:**
```json
{
    "pipeline_id": "pipeline-x1y2z3",
    "status": "completed",
    "total_tasks": 4,
    "completed_tasks": 4,
    "failed_tasks": 0,
    "current_phase": "aggregating"
}
```

## DAG Execution

### `POST /dag/execute`

**Request:**
```json
{
    "task": "执行数据处理流程",
    "sop_task_ids": ["step1", "step2"]
}
```

## Worker Management

### `POST /workers/register`

**Request:**
```json
{
    "worker_id": "coder-1",
    "skills": ["coding", "testing"],
    "endpoint": "http://localhost:8005"
}
```

### `GET /workers`

**Response:**
```json
{
    "workers": []
}
```

## Knowledge Search

### `POST /knowledge/search`

**Request:**
```json
{
    "query": "用户认证流程",
    "top_k": 5
}
```

**Response:**
```json
{
    "results": [
        {
            "doc_id": "doc-001",
            "content": "用户认证流程包括登录、注册、密码重置...",
            "source": "knowledge_graph",
            "score": 0.95
        }
    ]
}
```

## Metrics

### `GET /metrics`

**Response:**
```json
{
    "uptime_seconds": 3600.5,
    "modules": {
        "knowledge_retriever": {
            "avg_latency_ms": 45.2,
            "total_retrievals": 150,
            "recall_rate": 0.85,
            "empty_result_rate": 0.10,
            "cache_hit_rate": 0.65,
            "errors": 2
        }
    }
}
```

## Sessions

### `GET /agent/sessions`

**Response:**
```json
[
    {
        "session_id": "session-a1b2c3d4",
        "task": "Analyze user data...",
        "finished": true
    }
]
```

### `GET /agent/sessions/{session_id}`

**Response:**
```json
{
    "session_id": "session-a1b2c3d4",
    "task": "Analyze user behavior data",
    "finished": true,
    "result": "...",
    "steps": [...]
}
```

### `GET /tools`

**Response:**
```json
{
    "tools": [
        {"name": "shell", "description": "Execute a shell command"},
        {"name": "read_file", "description": "Read file content"},
        {"name": "write_file", "description": "Write content to file"},
        {"name": "list_files", "description": "List files in directory"},
        {"name": "search_files", "description": "Search keyword in files"},
        {"name": "http_get", "description": "Make HTTP GET request"}
    ]
}
```

## Data Models

### SubTask
```json
{
    "task_id": "subtask-a1b2c3d4",
    "title": "需求分析",
    "description": "分析功能需求和约束条件",
    "dependency": [],
    "required_skill": "analysis",
    "est_duration": 15,
    "context": {},
    "status": "pending",
    "assigned_worker": null,
    "result": null,
    "created_at": "2026-05-28T10:00:00"
}
```

### PipelineExecuteRequest
```json
{
    "task": "任务描述",
    "use_knowledge": true,
    "use_experience": true
}
```

### DAGExecuteRequest
```json
{
    "task": "任务描述",
    "sop_task_ids": ["step1", "step2"]
}
```
