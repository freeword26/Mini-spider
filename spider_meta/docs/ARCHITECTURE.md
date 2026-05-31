# spider_meta Architecture

## Positioning

**spider_meta (spider_meta)** is the command-and-control layer in a three-tier closed-loop multi-agent system.

```
┌─────────────────────────────────────────────────┐
│           spider_meta (Command Layer)            │
│  Task Understanding → Decomposition → Dispatch   │
├─────────────────────────────────────────────────┤
│         Worker Agents (Execution Layer)          │
│  Researcher / Coder / Cleaner                    │
├─────────────────────────────────────────────────┤
│        Resources & Environment Layer             │
│  Knowledge Graph / State Store / Message Bus     │
└─────────────────────────────────────────────────┘
```

## Core Modules

### 1. Data Layer (`core/schemas.py`)

| Model | Purpose |
|-------|---------|
| `SubTask` | Atomic task unit with dependencies, skills, context |
| `TaskTree` | Hierarchical task structure from decomposition |
| `WorkerCapability` | Worker registration with skills and load |
| `TaskIntent` | Parsed intent from task analysis |
| `TaskResult` | Aggregated pipeline execution result |
| `PipelineStatus` | Real-time pipeline tracking |
| `KnowledgeDoc` | Retrieved knowledge document |
| `Experience` | Stored execution experience |

### 2. Task Decomposition (`modules/task_decomposer.py`)

```
Input: "开发一个用户登录系统"
  ↓ _analyze_intent()
TaskIntent(intent_type="development", required_skills=["coding"])
  ↓ _generate_subtasks()
[需求分析, 方案设计, 编码实现, 测试验证]
  ↓ _decompose_recursive() [for complex subtasks]
[需求分析], [方案设计], [编码实现-准备, 编码实现-执行], [测试验证]
```

Supports both LLM-based and rule-based decomposition with configurable max depth.

### 3. Worker Dispatch (`core/worker_dispatcher.py`)

**Algorithm**: Weighted least-connections with capability matching
```
score(worker) = worker.load × (1 + worker.active_tasks)
```

**Heartbeat**: Redis-based with configurable timeout (default 5s). Graceful degradation to in-memory when Redis unavailable.

### 4. Pipeline Orchestration (`core/pipeline_orchestrator.py`)

```
understand → decompose → dispatch → aggregate
     ↓           ↓          ↓          ↓
 TaskIntent  TaskTree  assignments  TaskResult
```

### 5. DAG Engine (`core/dag_engine.py`)

- **Topological Sort**: Kahn's algorithm for layer-based parallel execution
- **SOP Hot-swap**: Runtime marking of subgraphs for serial execution
- **Dynamic Concurrency**: Auto-adjust based on worker load

### 6. Knowledge Retrieval (`modules/knowledge_retriever.py`)

```
Query → LRU Cache → ChromaDB Vector Search → Keyword Fallback
              ↓              ↓                      ↓
         <100ms         <2s timeout            graceful
```

### 7. Experience Management (`modules/experience_manager.py`)

SQLite-based storage of (task_summary, task_tree, worker_assignments) triples.
Keyword-based similarity retrieval for experience reuse.

## Data Flow

```
User Task
  → PipelineOrchestrator.execute()
    → _understand(): TaskIntent + Knowledge injection
    → _decompose(): TaskTree via TaskDecomposer
    → _dispatch(): Worker assignments via WorkerDispatcher
    → _aggregate(): TaskResult
      → ExperienceManager.store_experience()
```

## API Endpoints

| Method | Path | Module |
|--------|------|--------|
| GET | /health | main |
| GET | /health/detailed | main |
| POST | /agent/run | main |
| POST | /agent/plan | main |
| GET | /agent/sessions/{id} | main |
| GET | /agent/sessions | main |
| GET | /tools | main |
| POST | /pipeline/execute | orchestrator |
| GET | /pipeline/status/{id} | orchestrator |
| POST | /dag/execute | dag_engine |
| POST | /workers/register | dispatcher |
| GET | /workers | dispatcher |
| POST | /knowledge/search | retriever |
| GET | /metrics | monitoring |

## Configuration

All settings via `config/settings.yaml` or environment variables:

| Key | Default | Description |
|-----|---------|-------------|
| `redis_host` | localhost | Redis server host |
| `redis_port` | 6381 | Redis server port |
| `llm_model` | default | LLM model name |
| `llm_api_key` | "" | LLM API key |
| `kg_collection_name` | knowledge_graph | ChromaDB collection |
| `enable_knowledge_retrieval` | true | Knowledge retrieval toggle |
| `enable_experience_reuse` | true | Experience reuse toggle |
| `default_parallelism` | 3 | Default DAG concurrency |
| `worker_heartbeat_timeout` | 5 | Worker heartbeat TTL (s) |

## Extension Points

### Adding a New Worker Type

```python
dispatcher.register_worker(
    worker_id="analyst-1",
    skills=["analysis", "visualization"],
    endpoint="http://localhost:8005"
)
```

### Adding a New Skill

Register via `ToolRegistry` in `main.py`:

```python
tools.register("analyze_data", analyze_func, "Analyze dataset", {"path": "string"})
```

### Plugin Architecture

spider_meta supports skill plugins compatible with the broader Spider ecosystem:

```python
from spider_meta.plugins import SkillPlugin

class MySkill(SkillPlugin):
    name = "my_skill"
    version = "1.0.0"

    def activate(self, context):
        pass

    def execute(self, task):
        pass
```
