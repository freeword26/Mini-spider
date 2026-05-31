# Meta-Agent 接口规范文档

## 概述

本文档定义Meta-Agent元智能体的核心模块接口规范，涵盖数据Schema、模块接口及REST API端点。

## 数据Schema

### SubTask（子任务）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_id | str | 自动 | 唯一标识符，格式：subtask-{hash} |
| title | str | 是 | 子任务标题 |
| description | str | 否 | 详细描述 |
| dependency | List[str] | 否 | 依赖的任务ID列表 |
| required_skill | str | 是 | 所需技能标签 |
| est_duration | int | 否 | 预估耗时（分钟） |
| context | Dict[str, Any] | 否 | 上下文数据 |
| status | TaskStatus | 自动 | 任务状态：pending/running/completed/failed/cancelled |
| assigned_worker | Optional[str] | 否 | 分配的Worker ID |
| result | Optional[Any] | 否 | 执行结果 |
| created_at | str | 自动 | 创建时间（ISO格式） |

### TaskTree（任务树）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| root_id | str | 自动 | 根节点ID，格式：tree-{hash} |
| title | str | 是 | 任务标题 |
| description | str | 否 | 任务描述 |
| subtasks | List[SubTask] | 是 | 子任务列表 |
| max_depth | int | 否 | 最大递归深度，默认3 |
| created_at | str | 自动 | 创建时间（ISO格式） |

### WorkerCapability（Worker能力）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| worker_id | str | 是 | Worker唯一标识 |
| skills | List[str] | 是 | 技能列表 |
| load | float | 否 | 当前负载 0.0~1.0 |
| status | WorkerStatus | 否 | 在线状态：online/busy/offline |
| endpoint | str | 否 | 服务地址 |
| last_heartbeat | Optional[str] | 否 | 最后心跳时间 |
| active_tasks | int | 否 | 当前活跃任务数 |

### TaskIntent（任务意图）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| original_task | str | 是 | 原始任务文本 |
| intent_type | str | 否 | 意图类型 |
| complexity | str | 否 | 复杂度：low/medium/high |
| keywords | List[str] | 否 | 关键词列表 |
| required_skills | List[str] | 否 | 所需技能列表 |

### TaskResult（任务结果）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| pipeline_id | str | 是 | Pipeline唯一标识 |
| tree | TaskTree | 是 | 任务树 |
| status | TaskStatus | 自动 | 整体状态 |
| results | Dict[str, Any] | 否 | 各子任务结果 |
| errors | List[str] | 否 | 错误信息列表 |
| started_at | str | 自动 | 开始时间 |
| completed_at | Optional[str] | 否 | 完成时间 |

### PipelineStatus（Pipeline状态）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| pipeline_id | str | 是 | Pipeline唯一标识 |
| status | TaskStatus | 自动 | 当前状态 |
| total_tasks | int | 否 | 总任务数 |
| completed_tasks | int | 否 | 已完成任务数 |
| failed_tasks | int | 否 | 失败任务数 |
| current_phase | str | 否 | 当前阶段 |
| started_at | str | 自动 | 开始时间 |
| updated_at | str | 自动 | 更新时间 |

### KnowledgeDoc（知识文档）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| doc_id | str | 是 | 文档唯一标识 |
| content | str | 是 | 文档内容 |
| source | str | 否 | 来源 |
| score | float | 否 | 相关性分数 |
| metadata | Dict[str, Any] | 否 | 元数据 |

### Experience（经验）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| experience_id | str | 自动 | 经验唯一标识 |
| task_summary | str | 是 | 任务摘要 |
| task_tree_snapshot | Dict[str, Any] | 否 | 任务树快照 |
| worker_assignments | Dict[str, str] | 否 | Worker分配记录 |
| created_at | str | 自动 | 创建时间 |

## 模块接口

### TaskDecomposer（任务拆解器）

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| decompose | task: str, context: dict = None | TaskTree | 主拆解入口，将任务拆解为任务树 |
| _analyze_intent | task: str | TaskIntent | 分析任务意图 |
| _generate_subtasks | intent: TaskIntent | List[SubTask] | 根据意图生成子任务列表 |
| _decompose_recursive | subtask: SubTask, depth: int | List[SubTask] | 递归拆解子任务 |
| _infer_skill | subtask: SubTask | str | 推断子任务所需技能 |

### WorkerDispatcher（Worker调度器）

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| register_worker | worker_id: str, skills: List[str], endpoint: str | WorkerCapability | 注册Worker |
| heartbeat | worker_id: str, load: float | bool | 心跳更新 |
| dispatch | subtask: SubTask | Optional[str] | 任务分配，返回Worker ID |
| get_worker_status | worker_id: str | Optional[WorkerCapability] | 查询Worker状态 |
| list_available_workers | skill: str = None | List[WorkerCapability] | 列出可用Worker |

### PipelineOrchestrator（Pipeline协调器）

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| execute | task: str | TaskResult | 执行完整Pipeline |
| get_pipeline_status | pipeline_id: str | PipelineStatus | 查询Pipeline状态 |

### DAGEngine（DAG执行引擎）

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| build_graph | subtasks: List[SubTask] | DAG | 构建DAG图 |
| execute | dag: DAG, worker_dispatcher: WorkerDispatcher | Dict | 执行DAG |
| get_execution_order | dag: DAG | List[List[str]] | 获取拓扑执行顺序 |
| mark_subgraph_as_sop | task_ids: List[str] | None | 标记SOP子图 |
| adjust_concurrency | worker_loads: Dict[str, float] | None | 动态并行度调整 |

### KnowledgeRetriever（知识检索器）

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| retrieve | query: str, top_k: int = 5 | List[KnowledgeDoc] | 知识检索 |
| stats |  | Dict | 统计信息 |

### LLMService（LLM服务）

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| generate | messages: List[dict], context: dict = None | str | 生成响应 |
| supports_knowledge_retrieval |  | bool | 检查是否支持知识检索 |

### ExperienceManager（经验管理器）

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| store_experience | task_summary: str, task_tree: TaskTree, worker_assignments: Dict | None | 存储经验 |
| retrieve_similar | task: str, top_k: int = 3 | List[Experience] | 相似经验检索 |

## 枚举类型

### TaskStatus

| 值 | 说明 |
|----|------|
| pending | 等待中 |
| running | 执行中 |
| completed | 已完成 |
| failed | 失败 |
| cancelled | 已取消 |

### WorkerStatus

| 值 | 说明 |
|----|------|
| online | 在线 |
| busy | 忙碌 |
| offline | 离线 |

## REST API端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /health | 健康检查 |
| POST | /agent/run | 执行任务 |
| POST | /agent/plan | 创建计划 |
| GET | /agent/sessions/{session_id} | 获取会话 |
| GET | /agent/sessions | 列出会话 |
| GET | /tools | 列出工具 |
| POST | /pipeline/execute | 执行Pipeline |
| GET | /pipeline/status/{pipeline_id} | Pipeline状态 |
