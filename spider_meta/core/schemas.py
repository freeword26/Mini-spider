import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkerStatus(str, Enum):
    ONLINE = "online"
    BUSY = "busy"
    OFFLINE = "offline"


class SubTask(BaseModel):
    task_id: str = Field(default_factory=lambda: f"subtask-{uuid.uuid4().hex[:8]}")
    title: str = ""
    description: str = ""
    dependency: List[str] = Field(default_factory=list)
    required_skill: str = ""
    est_duration: int = 0
    context: Dict[str, Any] = Field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    assigned_worker: Optional[str] = None
    result: Optional[Any] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class TaskTree(BaseModel):
    root_id: str = Field(default_factory=lambda: f"tree-{uuid.uuid4().hex[:8]}")
    title: str = ""
    description: str = ""
    subtasks: List[SubTask] = Field(default_factory=list)
    max_depth: int = 3
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class WorkerCapability(BaseModel):
    worker_id: str = ""
    skills: List[str] = Field(default_factory=list)
    load: float = 0.0
    status: WorkerStatus = WorkerStatus.OFFLINE
    endpoint: str = ""
    last_heartbeat: Optional[str] = None
    active_tasks: int = 0


class TaskIntent(BaseModel):
    original_task: str
    intent_type: str = ""
    complexity: str = "medium"
    keywords: List[str] = Field(default_factory=list)
    required_skills: List[str] = Field(default_factory=list)


class TaskResult(BaseModel):
    pipeline_id: str
    tree: TaskTree
    status: TaskStatus = TaskStatus.PENDING
    results: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
    started_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None


class PipelineStatus(BaseModel):
    pipeline_id: str
    status: TaskStatus = TaskStatus.PENDING
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    current_phase: str = ""
    started_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class KnowledgeDoc(BaseModel):
    doc_id: str = ""
    content: str = ""
    source: str = ""
    score: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Experience(BaseModel):
    experience_id: str = Field(default_factory=lambda: f"exp-{uuid.uuid4().hex[:8]}")
    task_summary: str = ""
    task_tree_snapshot: Dict[str, Any] = Field(default_factory=dict)
    worker_assignments: Dict[str, str] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
