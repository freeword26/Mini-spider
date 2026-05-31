# Spider Meta — 定位声明

---

## 它是什么

**Spider Meta 是一个多智能体任务编排框架（Agent Orchestration Framework）**。

核心能力：**你给它一个任务，它自动拆解、分配、执行、汇总。**

---

## 它不是什么

| 不是 | 原因 |
|------|------|
| **不是大模型** | 它不训练、不推理、不生成语言。它调度别人去推理 |
| **不是 ChatGPT 替代品** | 它不直接回答问题。它把问题分配给专业的 Agent 去处理 |
| **不是单体应用** | 它不存储业务数据、不提供 UI、不处理具体业务逻辑 |
| **不是工作流引擎（如 Airflow）** | 它不做定时任务调度。它做的是**智能任务分解 + Agent 动态分配** |

---

## 核心定位：控制平面

```
┌─────────────────────────────────────────────────────────────┐
│                     Spider Meta（控制平面）                    │
│                                                             │
│   任务接收 → 智能拆解 → Agent 路由 → 并行执行 → 结果汇总      │
│                                                             │
│   它不执行业务。它决定谁去执行、怎么执行、执行完怎么汇报。       │
└─────────────────────────────────────────────────────────────┘
           │                    │                    │
    ┌──────▼──────┐     ┌──────▼──────┐     ┌──────▼──────┐
    │ mini_spider  │     │ spider_max   │     │ spidermax_   │
    │ (轻量爬虫)    │     │ (高性能爬虫)  │     │ room (协作)  │
    └─────────────┘     └─────────────┘     └─────────────┘
         Worker               Worker            SkillPlugin
```

**一句话定义**：spider_meta 是 Spider 生态的**大脑**。其他项目是**手脚**。大脑不干活，但决定干什么、谁来干、怎么干。

---

## 核心能力（5 件事）

### 1. 任务分解
```
输入: "开发一个用户登录系统"

输出:
  [1] 需求分析      → doc_processor (本地)
  [2] 技术方案      → architect_local (本地)  
  [3] 编写代码      → code_engineer (本地函数: write_code + shell)
  [4] 编写测试      → test_engineer (本地函数: run_test)
  [5] 部署上线      → devops_engineer (本地函数: docker_check + shell)
```

### 2. Agent 路由
```
任务内容 → 技能匹配 → 29 个角色评分
         + 预算检查 → 能不能花钱
         + GPU 检查 → 本地能不能跑
         → 最优角色分配
```

### 3. 并行执行
```
5 个子任务 → asyncio.gather 并行
           → git worktree 隔离
           → 全部完成 → 汇总报告
```

### 4. 成本控制
```
每次调用 → 记录 token → 计算费用
         → 日预算 ¥1.67 / 月预算 ¥50
         → 80% 告警 / 95% 强制降级到本地函数
```

### 5. 硬件保护
```
启动时检查: GPU ≤3.5GB, CPU ≤3核, RAM ≤16GB, 磁盘 ≤85%
运行时监控: 实时检测资源使用
超限处理: critical → 拒绝启动 / warning → 降级运行
```

---

## 技术架构（10 层）

```
层 1: 任务接收     → FastAPI (34 个端点)
层 2: 任务拆解     → TaskDecomposer (规则 + LLM)
层 3: DAG 编排     → 拓扑排序 + 并行/串行
层 4: Agent 路由   → Router (29 角色匹配 + 预算 + GPU 检查)
层 5: 本地执行     → HybridLocalAgent (函数优先, Ollama 兜底)
层 6: 云端执行     → CloudAgent (DeepSeek/GPT-4o-mini)
层 7: 差分卸载     → DifferentialOffloader (能力边界判断)
层 8: 通讯协议     → DeltaSync (99.2% 带宽降低)
层 9: 成本控制     → BudgetManager (日/月追踪 + 自动降级)
层10: 硬件保护     → HARDWARE_LIMITS (启动检查 + 运行时监控)
```

---

## 部署方式

```bash
# 一键启动
docker compose up -d

# 服务端口
# spider-meta API:  http://localhost:8003
# Redis:            localhost:6379

# 资源限制 (Docker)
# CPU: 3核 | RAM: 16GB | GPU: 3.5GB
```

---

## 关键代码文件（12 个核心文件）

| 文件 | 行数 | 职责 |
|------|------|------|
| main.py | 856 | 全部 API 端点 + 启动检查 |
| config.py | 149 | 配置 + 硬件限制 + 启动检查 |
| cost_guard.py | 322 | 预算追踪 + 定价表 + 自动降级 |
| agents/agent_router.py | 816 | 29 角色定义 + 路由决策 + 差分卸载 |
| agents/agent_manager.py | 439 | 并行调度 + git worktree 隔离 |
| agents/local/__init__.py | 378 | HybridLocalAgent + 角色技能函数映射 |
| agents/cloud/__init__.py | 113 | CloudAgent 云端 API 封装 |
| agents/protocol.py | 447 | DeltaSync + LiteCapabilityProxy |
| core/pipeline_orchestrator.py | 125 | Pipeline 四阶段编排 |
| core/dag_engine.py | 145 | DAG 拓扑排序 + SOP 热切换 |
| core/worker_dispatcher.py | 184 | Worker 注册/心跳/分配 |
| core/event_bus.py | 233 | 事件发布/订阅 |

---

## 一句话总结

**spider_meta = 任务拆解器 + Agent 路由器 + 并行执行器 + 成本控制阀 + 硬件保护壳**

它不执行业务，它让对的 Agent 在对的时间用对的方式执行对的任务。
