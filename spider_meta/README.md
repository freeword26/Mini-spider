# spider_meta — 产品功能说明

## 这个项目是干用的？

**spider_meta 是一个 AI 智能体编排框架**。你给它一个任务描述，它自动完成以下的事：

1. **理解任务** — 分析你要做什么
2. **拆解任务** — 把大任务拆成若干小步骤
3. **执行任务** — 调用各种工具（Shell命令、文件读写、HTTP请求等）逐步完成
4. **汇总结果** — 把执行过程和结果返回给你

一句话：**你只说"做什么"，它来想"怎么做"。**

---

## 核心功能

### 1. 🤖 Meta-Agent（智能体）
一个能自主思考和执行任务的 AI Agent。

**使用方式：** 给它一段自然语言任务描述，它会自动推理、选择工具、执行操作、观察结果，循环直到任务完成。

**例子：**
```
你说："统计当前目录下所有 Python 文件的行数"

Meta-Agent 自动执行：
Step 1: 用 list_files 列出所有 .py 文件
Step 2: 用 read_file 逐个读取文件内容
Step 3: 统计行数并汇总
Result: "共 12 个 Python 文件，总计 3,456 行"
```

它内置 6 个工具：
| 工具 | 功能 |
|------|------|
| shell | 执行 Shell 命令 |
| read_file | 读取文件内容 |
| write_file | 写入文件 |
| list_files | 列出目录文件 |
| search_files | 在文件中搜索关键词 |
| http_get | 发起 HTTP 请求 |

### 2. 📋 Pipeline（流水线编排）
把任务自动拆分成有依赖关系的子任务，按顺序或并行执行。

**四阶段流程：**
```
理解(Understand) → 分解(Decompose) → 调度(Dispatch) → 汇总(Aggregate)
```

**例子：**
```
输入："开发一个 REST API"

自动拆解为：
[1] 需求分析      ──→ [2] 技术方案设计 ──→ [3] 编写代码 ──→ [4] 测试验证

其中 [3] 和 [4] 可以并行：
                ┌──→ [3a] 数据库设计 ──┐
[2] ────────────┤                     ├──→ [4] 测试
                └──→ [3b] API编码   ──┘
```

### 3. 🔀 DAG 引擎（有向无环图执行）
管理复杂任务的依赖关系，支持：
- **拓扑排序** — 自动计算执行顺序
- **并行执行** — 没有依赖的任务同时运行
- **循环检测** — 发现死循环立即报错
- **SOP热切换** — 运行时动态将某个子流程改为串行（比如测试阶段必须逐个执行）

### 4. 👷 Worker 分布式调度
多台机器可以注册为 Worker，系统自动分配任务。

- **技能注册**：每个 Worker 声明自己擅长什么（coding / analysis / search...）
- **智能匹配**：根据任务需求找到最合适的 Worker
- **负载均衡**：优先分配给当前任务最少的 Worker
- **心跳保活**：自动检测 Worker 是否在线，掉线自动转移任务

**架构图：**
```
任务来了 → Pipeline编排器 → DAG引擎计算执行顺序
                                    ↓
                         ┌──────────┼──────────┐
                         ↓          ↓          ↓
                    Worker-A    Worker-B    Worker-C
                    (代码编写)   (数据分析)    (文档检索)
                         └──────────┼──────────┘
                                    ↓
                              汇总结果返回
```

### 5. 📚 知识检索（可选）
执行任务前，先从知识库中检索相关背景资料，提升执行质量。

- 基于 ChromaDB 的向量语义搜索（找"意思相近"的内容）
- 关键词精确匹配兜底
- LRU 缓存，相同查询不重复检索

**流程：**
```
任务输入 → 向量化 → 在知识库中搜索 → 找到相关文档 → 注入到任务上下文中 → 执行
```

### 6. 🧠 经验复用（可选）
自动记录每次任务执行的经验，下次遇到相似任务时参考历史方案。

- SQLite 存储：(任务摘要, 任务树快照, Worker 分配记录)
- 关键词相似度匹配
- 避免重复踩坑，提升执行效率

### 7. 📡 事件系统
整个框架基于事件驱动，任何操作都会产生事件：

| 事件类型 | 说明 |
|---------|------|
| task.submitted | 任务已提交 |
| task.decomposed | 已拆分子任务 |
| task.assigned | 已分配 Worker |
| task.completed | 任务完成 |
| task.failed | 任务失败 |
| worker.registered | Worker 注册 |
| worker.heartbeat | Worker 心跳 |

可以订阅这些事件实现自动化流水线，比如"当任务自动分解完成后，立即触发执行"。

### 8. 📊 监控指标
实时收集运行数据：
- 检索延迟（平均响应时间）
- 召回率（知识检索的准确率）
- 缓存命中率
- 错误计数

---

## 使用场景

| 场景 | 说明 |
|------|------|
| **自动化运维** | "检查服务器状态，如果负载超过80%就清理日志" |
| **代码开发** | "给这个项目添加用户登录功能" |
| **数据分析** | "分析这份CSV数据，生成可视化报告" |
| **文档处理** | "搜索所有包含'合同'关键词的文件，汇总金额" |
| **知识问答** | "从知识库中查找关于支付流程的文档" |

---

## 快速上手

### 安装
```bash
pip install -e ".[all]"
```

### 启动
```bash
python -m spider_meta.main
```

### 执行任务
```bash
# 单 Agent 模式（直接执行）
curl -X POST http://localhost:8003/agent/run \
  -H "Content-Type: application/json" \
  -d '{"task": "统计当前目录的文件数量", "max_steps": 5}'

# Pipeline 模式（自动拆解 → 执行 → 汇总）
curl -X POST http://localhost:8003/pipeline/execute \
  -H "Content-Type: application/json" \
  -d '{"task": "开发一个文件搜索工具", "use_knowledge": true}'

# 查看系统状态
curl http://localhost:8003/health
curl http://localhost:8003/metrics
```

### 接入 LLM
配置环境变量启用真正的 AI 推理能力：
```bash
export LLM_API_URL="https://openrouter.ai/api/v1"
export LLM_API_KEY="your-api-key"
python -m spider_meta.main
```
不配置 LLM 时，系统使用内置的模拟推理引擎，适合测试和简单任务。

---

## 扩展方式

### 添加自定义工具
向 Meta-Agent 注册新技能：
```python
from spider_meta.main import tools

async def my_custom_tool(query: str) -> str:
    # 你的业务逻辑
    return f"处理结果: {query}"

tools.register("my_tool", my_custom_tool, "自定义业务工具", {"query": "string"})
```

### 编写插件
```python
from spider_meta.plugins import SkillPlugin, register_skill

@register_skill
class DataAnalysisSkill(SkillPlugin):
    name = "data_analysis"
    version = "1.0.0"
    description = "数据分析技能"

    def activate(self, context):
        pass

    async def execute(self, task):
        # 执行数据分析
        return {"status": "done", "records_processed": 1000}
```

---

## 十、Spider 生态与注册机制

### 生态全景

spider_meta 是 Spider 生态的**控制平面（Control Plane）**，本身不执行业务，而是把所有 Spider 子项目编排成一个有机的智能体网络。

```
┌──────────────────────────────────────────────────────────────┐
│                      Spider 生态系统                          │
│                                                              │
│  ┌──────────────────── 控制层 ────────────────────┐          │
│  │                                                 │          │
│  │            spider_meta (本项目)                  │          │
│  │    任务分解 │ 智能调度 │ DAG编排 │ 事件驱动       │          │
│  │                                                 │          │
│  └──────────────────────┬──────────────────────────┘          │
│                         │ 注册 & 调度                          │
│         ┌───────────────┼───────────────┐                     │
│         │               │               │                     │
│  ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐             │
│  │   执行层     │ │   经验层     │ │   扩展层     │             │
│  │             │ │             │ │             │             │
│  │ mini_spider │ │spider_diary │ │  Spider-X   │             │
│  │ (轻量爬虫)   │ │ (日志/经验)  │ │ (扩展适配)   │             │
│  │             │ │             │ │             │             │
│  │ spider_max  │ │             │ │spidermax_   │             │
│  │ (高性能爬虫) │ │             │ │  room       │             │
│  └─────────────┘ └─────────────┘ │ (协作空间)   │             │
│                                  └─────────────┘             │
└──────────────────────────────────────────────────────────────┘
```

### 子项目与注册表

| 项目 | 一句话说明 | 注册方式 | spider_meta 调它做什么 |
|------|-----------|---------|---------------------|
| **mini_spider** | 轻量爬虫节点 | `POST /workers/register` | 爬取网页、数据采集 |
| **spider_max** | 高性能分布式爬虫 | `POST /workers/register` | 大规模爬取、JS渲染、反爬 |
| **Spider-X** | 扩展适配层 | `@register_skill` 插件 | 第三方API对接、自定义协议 |
| **spider_diary** | 爬取日志与经验库 | `tools.register()` | 存储执行日志、查询历史经验 |
| **spidermax_room** | 虚拟协作空间 | `@register_skill` 插件 | 多Agent协作、任务协调 |

### 四种注册方式

根据集成深度，spider_meta 提供从轻到重的四种注册方式：

---

#### 方式一：Worker 注册（最轻量）

**适用**：mini_spider、spider_max 等有独立 HTTP 服务的执行节点

**原理**：Worker 向 spider_meta 声明"我在哪、会什么"，spider_meta 通过技能匹配自动分配任务。

```bash
# mini_spider 注册
curl -X POST http://spider-meta:8003/workers/register \
  -H "Content-Type: application/json" \
  -d '{
    "worker_id": "mini-spider-01",
    "skills": ["crawl", "fetch", "parse"],
    "endpoint": "http://mini-spider:8001"
  }'

# spider_max 注册
curl -X POST http://spider-meta:8003/workers/register \
  -H "Content-Type: application/json" \
  -d '{
    "worker_id": "spider-max-01",
    "skills": ["distributed_crawl", "js_render", "anti_crawl"],
    "endpoint": "http://spider-max:8002"
  }'
```

注册后，当 Pipeline 分解出需要"crawl"技能的任务时，自动分配给对应 Worker。

---

#### 方式二：Tool 注册（轻量）

**适用**：spider_diary 等提供单一功能的工具型服务

**原理**：把外部服务封装成一个函数，注册到 Meta-Agent 的工具Registry 中。

```python
from spider_meta.main import tools
import httpx

async def diary_log(task_id: str, content: str) -> str:
    """spider_diary: 记录执行日志"""
    async with httpx.AsyncClient() as client:
        await client.post("http://spider-diary:8001/log", json={
            "task_id": task_id, "content": content
        })
    return f"日志已记录: {task_id}"

async def diary_query(query: str, limit: int = 5) -> dict:
    """spider_diary: 查询历史经验"""
    async with httpx.AsyncClient() as client:
        resp = await client.get("http://spider-diary:8001/query", params={
            "q": query, "limit": limit
        })
        return resp.json()

tools.register("diary_log", diary_log, "spider_diary 日志记录",
               {"task_id": "string", "content": "string"})
tools.register("diary_query", diary_query, "spider_diary 经验查询",
               {"query": "string", "limit": "number"})
```

注册后，Meta-Agent 在执行过程中可以自主调用这些工具。

---

#### 方式三：SkillPlugin 插件（标准）

**适用**：Spider-X、spidermax_room 等需要生命周期管理和参数验证的复杂扩展

**原理**：实现 SkillPlugin 接口，注册到全局 PluginRegistry。

```python
from spider_meta.plugins import SkillPlugin, register_skill
import httpx

@register_skill
class SpiderXAdapter(SkillPlugin):
    """Spider-X: 第三方 API 扩展适配器"""

    name = "spider_x"
    version = "1.0.0"
    description = "通过 Spider-X 调用第三方 API"

    def activate(self, context):
        """启动时加载配置"""
        self.api_base = context.get("api_base", "http://spider-x:8000")
        self.api_key = context.get("api_key", "")

    async def execute(self, task):
        """转发请求到 Spider-X"""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.api_base}/adapt",
                json={"task": task},
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            return resp.json()

    def validate(self, params):
        return "api_base" in params

    def deactivate(self):
        """清理资源"""
        pass


@register_skill
class SpiderMaxRoomSkill(SkillPlugin):
    """spidermax_room: 多Agent协作空间"""

    name = "spider_room"
    version = "1.0.0"
    description = "创建虚拟协作空间，协调多Agent完成任务"

    def activate(self, context):
        self.room_endpoint = context.get(
            "room_endpoint", "http://spidermax-room:8000"
        )

    async def execute(self, task):
        """在协作空间中分配子任务"""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.room_endpoint}/room/create",
                json={"task": task}
            )
            room_id = resp.json()["room_id"]
            return {"room_id": room_id, "status": "collaborating"}

    def validate(self, params):
        return "room_endpoint" in params
```

---

#### 方式四：Event 订阅（自动化）

**适用**：任何需要响应系统状态变化、实现自动化流水线的场景

**原理**：订阅事件总线上的特定事件，事件触发时自动执行回调。

```python
from spider_meta.core.event_bus import event_bus, EventType

# 示例：任务完成后自动记录到 diary
async def on_task_completed(event):
    """当任务完成时，自动写入 spider_diary"""
    task_data = event.data
    await diary_log(task_data["task_id"], task_data["result"])

event_bus.subscribe([EventType.TASK_COMPLETED], on_task_completed)

# 示例：DAG执行完成后自动触发通知
async def on_dag_finished(event):
    dag_info = event.data
    print(f"DAG {dag_info['dag_id']} 执行完毕，"
          f"成功: {dag_info['completed']}, 失败: {dag_info['failed']}")

event_bus.subscribe([EventType.DAG_EXECUTION_COMPLETED], on_dag_finished)
```

---

### 项目元数据

每个注册到生态中的项目，应在 spider_meta 中有对应的元数据记录：

```json
{
  "project_id": "PRJ_SPIDER_META_001",
  "project_name": "spider_meta",
  "family": "meta",
  "role": "Spider生态元智能体编排框架",
  "version": "0.5.0",
  "upstream": null,
  "downstream": [
    {"id": "PRJ_MINI_SPIDER_001",  "name": "mini_spider",     "registered_as": "worker"},
    {"id": "PRJ_SPIDER_MAX_001",   "name": "spider_max",      "registered_as": "worker"},
    {"id": "PRJ_SPIDER_DIARY_001", "name": "spider_diary",    "registered_as": "tool"},
    {"id": "PRJ_SPIDER_X_001",     "name": "Spider-X",        "registered_as": "skill_plugin"},
    {"id": "PRJ_SMR_001",          "name": "spidermax_room",  "registered_as": "skill_plugin"}
  ]
}
```

`family = "meta"` 表示 spider_meta 是生态的**元层**——它本身不爬取数据、不存储文件、不调用第三方 API，而是**指挥**谁去干这些事。
