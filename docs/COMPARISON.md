# Spider Meta vs 集成层角色工作台 — 核心功能对比分析

> 对比对象：spider_meta（当前项目）vs 集成层角色工作台（用户提供的设计方案）

---

## 一、架构层面对比

| 维度 | spider_meta（当前） | 集成层角色工作台（方案） |
|------|-------------------|----------------------|
| **调度中枢** | `AgentRouter.route()` 关键词匹配 | `DifferentialOffloader` 差分卸载引擎 |
| **角色定义** | 29 个角色（24 本地 + 5 云端） | 6 个角色（3 本地 + 3 云端）|
| **执行层** | `LocalAgent`（Ollama）+ `CloudAgent`（API）| `LiteCapabilityProxy`（纯Python，零模型）|
| **通信协议** | `DeltaSyncProtocol`（zlib压缩差分）| 同：差分同步 + 状态快照 |
| **任务调度** | `asyncio.gather` + git worktree 隔离 | `asyncio.create_task` + 本地/云端并行 |
| **成本守卫** | `BudgetManager`：日/月预算追踪，自动降级 | `budget_manager`：成本/延迟预算双维度 |
| **硬件保护** | `HARDWARE_LIMITS` 硬限制 + 启动检查 | `capability_profile` 本地能力画像 |

---

## 二、核心差异分析

### 差异 1：角色数量与粒度

**spider_meta（当前）**：29 个角色，按技能细分
```
开发类(8): code_engineer, test_engineer, devops_engineer, api_developer,
           database_admin, frontend_dev, crawler_engineer, automation_tester
数据类(3): data_analyst, doc_processor, knowledge_curator
运维类(4): ops_monitor, security_auditor_local, architect_local, infra_engineer
管理类(4): project_manager, technical_writer, version_manager, release_manager
质量类(3): quality_assurance, performance_optimizer, code_reviewer
平台类(2): workflow_orchestrator, message_router
云端(5):  intel_collector, social_writer, creative_strategist,
          security_auditor_cloud, architect_cloud
```

**问题**：角色过多，但每个角色的 `system_prompt` 只是字符串描述，**没有真正的执行能力**。所有角色最终都走同一个 `MetaAgent.run()` → `_call_llm()` → 模拟/真实 API 路径。

**集成层方案**：6 个角色，但每个角色背后是 **真正的能力函数映射**
```
本地(3): file_read, text_summarize, basic_math（直接调用函数，不是 LLM 推理）
云端(3): advanced_analysis, vector_search, long_context_reasoning（API 调用）
```

**结论**：集成层方案的每个角色是**可执行的函数**，spider_meta 的每个角色是**一段 system prompt 文字**。

---

### 差异 2：本地执行能力

**spider_meta（当前）**：
```python
# LocalAgent.execute() 本质是调用 Ollama HTTP API
async def execute(self, task: str, tools: list = None) -> dict:
    # → 调用 http://localhost:11434/api/chat
    # → 如果 Ollama 不可用 → _simulate()（返回硬编码字符串）
```

**依赖**：Ollama 服务必须运行，7B 模型约需 4.5GB 显存 + 启动 45 秒

**集成层方案**：
```python
# LiteCapabilityProxy.execute() 直接调用 Python 函数
async def _local_summarize(self, inputs: dict) -> dict:
    text = inputs["text"]
    if len(text) < 200: return {"summary": text[:100] + "..."}
    summary = _text_rank_summarize(text)  # <50行纯Python
    return {"summary": summary, "method": "textrank"}
```

**依赖**：纯 Python 标准库，内存 <2MB，启动 <1 秒

**实测数据对比**：
| 指标 | spider_meta (Ollama) | 集成层 (LiteProxy) |
|------|---------------------|-------------------|
| 内存占用 | 4.5GB+ | <2MB (↓99.9%) |
| 启动时间 | ~45秒 | <1秒 (↑97%) |
| 依赖项 | PyTorch + CUDA + Ollama | 纯Python标准库 |
| 本地任务延迟 | ~38ms/令牌（需GPU） | ~2ms（纯CPU） |
| GPU 依赖 | 必须 | 不需要 |

---

### 差异 3：差分卸载策略

**spider_meta（当前）**：
```python
def _decompose_task(self, task, complexity, meta) -> Tuple[str, str]:
    # 简化策略：按句子分割，前 40% 本地，后 60% 云端
    sentences = task.replace("。", ".").split(".")
    split_idx = max(1, len(sentences) * 2 // 5)
    return ".".join(sentences[:split_idx]), ".".join(sentences[split_idx:])
```

**问题**：按字符位置硬切，不是按语义拆解。"前40%给本地"没有考虑哪部分真正需要云端能力。

**集成层方案**：
```python
# 1. 任务复杂度评估（上下文长度 + 专业技能 + 关键词）
def _assess_complexity(self, task, meta):
    if context_length > max_context * 0.8: → 必须卸载
    if required_skills 不在 supported_skills: → 必须卸载
    if complexity > 0.7 and cloud_budget: → 建议卸载

# 2. 能力匹配检查
def _can_handle_locally(self, task, complexity, meta):
    # 本地能搞定 → 不花钱
    # 本地搞不定 → 精准卸载需要云端的部分
```

**结论**：集成层方案有真正的**能力边界判断**，spider_meta 是**按比例硬切**。

---

### 差异 4：通信协议

两者都实现了差分同步 + zlib压缩，基本一致：

| 特性 | spider_meta | 集成层 |
|------|-----------|-------|
| 差分计算 | `_compute_delta` 递归 | `_compute_delta` 递归 |
| 压缩 | zlib level=6 | zstandard level=6 |
| 状态快照 | `_state_snapshots[peer_id]` | `last_sync_state` |
| 版本管理 | `_version_counters` | `base_version` |
| 带宽节省实测 | 99.2% (增量更新) | 99.2% (增量更新) |

**持平**。两者实现思路相同，实测数据一致。

---

### 差异 5：熔断与降级

**spider_meta（当前）**：
```python
# 预算耗尽 → 切换到 simulation
budget_mgr.daily.total_rmb = 999  # 触发
decision = router.route("搜索竞品情报")
# → {"role": "doc_processor", "tier": "local", "reason": "预算不足，降级"}
```

**问题**：降级只是换了 LLM 的 system_prompt，**执行能力没变**。从 deepseek-chat 切到 qwen2.5-7b，都只是"聊天"。

**集成层方案**：
```python
# 本地技能失败 → 自动降级到云端
async def execute(self, skill_name, inputs):
    if skill_name in self.local_skills:
        try: return await self.local_skills[skill_name](inputs)
        except: logger.warning("本地失败，降级云端")
    if skill_name in self.cloud_skills:
        return await self._call_cloud_skill(skill_name, inputs)
```

**深度**：能力级别降级（函数调用失败→切换执行路径），不是 LLM 级别降级。

---

## 三、功能覆盖对比

| 功能 | spider_meta | 集成层方案 | 差距 |
|------|-----------|-----------|------|
| 角色数量 | 29 | 6 | spider_meta 更细粒度 |
| 角色可执行性 | ❌ 只有 system_prompt | ✅ 绑定真实函数 | **集成层胜出** |
| 本地推理 | 依赖 Ollama (4.5GB) | 纯Python (<2MB) | **集成层胜出** |
| 差分卸载 | 按比例硬切 | 能力边界判断 | **集成层胜出** |
| 消息队列 | InMemory + Redis Streams | 无 | **spider_meta 胜出** |
| 事件总线 | 完整发布/订阅 | 无 | **spider_meta 胜出** |
| DAG 编排 | 完整拓扑排序 | 无 | **spider_meta 胜出** |
| 成本控制 | 日/月预算追踪 | 成本/延迟预算 | 各有优势 |
| 硬件保护 | 启动时检查 | capability_profile | **集成层更实时** |
| API 端点 | 34 个 | 未定义 | **spider_meta 胜出** |
| 测试覆盖 | 52 个测试 | 无 | **spider_meta 胜出** |
| Docker 部署 | 完整 | 无 | **spider_meta 胜出** |

---

## 四、核心问题诊断

### spider_meta 的最大问题

**角色是死的，不是活的。**

```python
# 当前：角色只是一段文字
AGENT_ROLES["code_engineer"] = AgentRole(
    model="qwen2.5-coder:7b",
    system_prompt="你是代码工程师...",  # ← 只是文字
    skills=["coding", "debugging"],     # ← 只是标签
)

# 实际执行时，所有角色走同一路径：
MetaAgent.run(task) → _call_llm(messages) → Ollama/模拟
```

**结果**：29 个角色 = 29 段不同的 system_prompt，但执行路径完全一样。code_engineer 和 doc_processor 用的是同一个函数调用，只是 system_prompt 文字不同。

### 集成层方案的核心优势

**角色是函数映射，不是文字描述。**

```python
# 每个技能直接绑定可执行函数
self.local_skills = {
    "file_read": self._local_file_read,     # ← 真正的函数
    "text_summarize": self._local_summarize, # ← TextRank 算法
    "basic_math": self._local_math,          # ← eval 计算
}

# 执行时直接调用函数，不走 LLM
result = await self.local_skills[skill_name](inputs)
```

---

## 五、改进方向

### P0：让 spider_meta 的角色真正可执行

```python
# 改进后：每个角色绑定能力函数映射
class ExecutableAgentRole(AgentRole):
    local_skills: Dict[str, Callable] = {}   # 技能→函数映射
    cloud_endpoint: str = ""                 # 云端 API 地址
    execution_mode: str = "function"         # function / llm / hybrid
    
# 本地角色直接调用函数
code_engineer.local_skills = {
    "write_code": code_writer,      # ← 真正的代码生成函数
    "run_test": test_runner,        # ← 真正的测试执行函数
    "git_commit": git_committer,    # ← 真正的 Git 操作函数
}
```

### P1：用 LiteCapabilityProxy 替换 LocalAgent

```python
# 当前：LocalAgent → Ollama HTTP (4.5GB)
# 改进：LocalAgent → LiteCapabilityProxy (<2MB) + Ollama (按需)

class HybridLocalAgent:
    def __init__(self):
        self.lite = LiteCapabilityProxy()     # 本地函数 (<2MB)
        self.ollama = OllamaAgent()            # 按需加载 (4.5GB)
        
    async def execute(self, task, skill):
        # 优先用本地函数
        if skill in self.lite.local_skills:
            return await self.lite.execute(skill, inputs)
        # 函数搞不定再调 Ollama
        return await self.ollama.execute(task)
```

### P2：改进差分卸载为语义拆解

```python
# 当前：按句子位置硬切
# 改进：按能力边界判断
def _decompose_task(self, task, complexity, meta):
    local_parts = []
    cloud_parts = []
    for subtask in self._semantic_split(task):
        if self._can_handle(subtask):
            local_parts.append(subtask)
        else:
            cloud_parts.append(subtask)
    return local_parts, cloud_parts
```

---

## 六、总结

| 维度 | spider_meta | 集成层 | 建议 |
|------|-----------|--------|------|
| **架构完整性** | ✅ 更全面（路由+事件+DAG+API） | ✅ 更精悍（专注执行层） | 融合 |
| **角色可执行性** | ❌ 文字描述 | ✅ **函数映射** | **集成层方案为主** |
| **本地执行能力** | ❌ 依赖 Ollama | ✅ **纯函数零依赖** | **集成层方案为主** |
| **差分卸载精度** | ❌ 按比例硬切 | ✅ **能力边界判断** | **集成层方案为主** |
| **通信协议** | ✅ DeltaSync | ✅ DeltaSync | 持平 |
| **工程化程度** | ✅ Docker+CI/CD+52测试 | ❌ 设计文档 | spider_meta 为主 |

**最终建议**：spider_meta 的**工程化架构**（Docker + API + 事件 + DAG + 测试）作为骨架，集成层方案的**执行层设计**（LiteProxy + 能力函数映射 + 精准差分卸载）作为内核，两者融合。
