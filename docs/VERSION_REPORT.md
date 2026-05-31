# Spider 生态项目版本迭代报告

> 统计时间：2026-05-30
> 数据来源：metadata.json + 实际代码扫描 + git log

---

## 一、spider_meta（元智能体编排框架）

**当前版本：v0.5.0 | 状态：开发中 | 进度：80%**

这是 Spider 生态的**控制平面**，负责任务分解、智能调度、DAG 编排、事件驱动。

### 版本迭代

```
v0.1.0 (2026-05-20)  初始 scaffold
  ├── 核心 schemas 定义（SubTask, TaskTree, WorkerCapability 等）
  ├── 基础 Pipeline 编排器
  ├── Worker 调度器（注册、心跳、分配）
  ├── 配置系统（settings.yaml + pydantic-settings）
  └── MIT License + README

v0.5.0 (2026-05-28~30)  合并两个 Meta-Agent 项目 + 功能完善
  ├── 合并 event_bus.py（事件总线）
  ├── 合并 event_consumer.py（事件消费者 + TaskAutoAssigner）
  ├── 合并完整测试套件（52 个测试，全部通过）
  ├── 新增 Docker 部署（Dockerfile + docker-compose.yml）
  ├── 新增 .github/workflows/ci.yml（GitHub Actions CI/CD）
  ├── 新增 CHANGELOG.md
  ├── 修复 _get_redis() Redis 超时卡顿问题
  ├── 修复 _is_worker_alive() Worker 误判离线问题
  ├── worker_heartbeat_timeout 默认值 5s → 60s
  ├── /workers/register 端点接入真实 WorkerDispatcher
  ├── /workers 端点返回真实 Worker 列表
  ├── PluginRegistry ↔ ToolRegistry 双向绑定
  └── @register_skill 插件自动作为工具出现在 /tools
```

### 代码规模

| 指标 | 数值 |
|------|------|
| Python 文件 | 27 个 |
| 测试文件 | 4 个（52 个测试用例） |
| API 端点 | 14 个 |
| Docker | ✅ |
| CI/CD | ✅ |

### 里程碑

| 里程碑 | 状态 | 日期 |
|--------|------|------|
| 核心框架 | ✅ 完成 | 2026-05-20 |
| 元数据管理 | ✅ 完成 | 2026-05-24 |
| 插件系统 | ✅ 完成 | 2026-05-27 |
| 生态注册机制 | ✅ 完成 | 2026-05-30 |
| 上线发布 | 🔄 待启动 | TBD |

---

## 二、spider_max（全栈项目管理与多Agent协同平台）

**当前版本：v3.0.0 | 状态：已上线 | 进度：100%**

这是 Spider 生态的**核心执行引擎**，功能最全、代码量最大。

### 版本迭代

```
v1.0.0 (2026-05-20)  初始版本
  ├── 基础项目结构
  ├── 元数据管理
  └── 启动器 + README

v3.0.0 (2026-05-30)  全栈升级
  ├── 47 个服务模块
  ├── 14 个 API 端点
  ├── 15 个工作流
  ├── 23 个数据库表
  ├── Docker 镜像：spider-max:3.0.0
  ├── docker-compose.unattended.yml（无人值守配置）
  ├── OKR 追踪
  ├── DAG 任务调度
  ├── 监控告警
  └── 无人值守执行引擎
```

### 代码规模

| 指标 | 数值 |
|------|------|
| Python 文件 | 2097 个 |
| 服务模块 | 47 个 |
| API 端点 | 14 个 |
| 数据库表 | 23 个 |
| Docker | ✅ |

### 里程碑（全部完成）

| 里程碑 | 状态 | 日期 |
|--------|------|------|
| 核心架构 | ✅ | 2026-05-20 |
| 服务模块 | ✅ | 2026-05-22 |
| API 接口 | ✅ | 2026-05-24 |
| 数据迁移 | ✅ | 2026-05-26 |
| 上线发布 | ✅ | 2026-05-30 |

---

## 三、mini_spider（轻量爬虫节点）

**当前版本：v1.0.0 | 状态：已上线 | 进度：100%**

轻量级数据采集与自动化流水线，作为 Worker 注册到 spider_meta。

### 版本迭代

```
v1.0.0 (2026-05-15~20)  初始版本
  ├── 数据采集模块
  ├── 自动化流水线
  ├── CLI 工具
  └── 测试覆盖
```

### 代码规模

| 指标 | 数值 |
|------|------|
| Python 文件 | 19 个 |
| Docker | ❌ |
| 注册方式 | Worker（`POST /workers/register`） |

### 里程碑（全部完成）

| 里程碑 | 状态 | 日期 |
|--------|------|------|
| 数据采集 | ✅ | 2026-05-15 |
| 自动化流水线 | ✅ | 2026-05-18 |
| 工具发布 | ✅ | 2026-05-20 |

---

## 四、spider_diary（爬取日志与经验存储）

**当前版本：v1.0.0 | 状态：开发中 | 进度：约 70%**

spider_meta 的**经验层**，负责存储执行日志、查询历史经验。

### 代码规模

| 指标 | 数值 |
|------|------|
| Python 文件 | 25 个 |
| Docker | ✅ |
| 注册方式 | Tool（`tools.register()`） |

### 核心模块

- `core/project_reader.py` — 项目读取
- `core/system_checker.py` — 系统检查
- `storage/project_db.py` — SQLite 项目数据库
- `report/report_generator.py` — 报告生成
- `remind/remind_engine.py` — 提醒引擎
- `remind/blocker_store.py` — 阻塞项存储

---

## 五、spidermax_room（虚拟协作空间）

**当前版本：v2.0.0 | 状态：已上线 | 进度：100%**

spider_meta 的**扩展层**，多 Agent 协作空间，作为 SkillPlugin 注册。

### 版本迭代

```
v1.0.0  初始版本
  ├── 虚拟协作空间基础功能
  └── 多 Agent 协调

v2.0.0 (2026-05-30)  Docker 完善
  ├── Docker 部署完善
  ├── .dockerignore 优化
  └── 完整开源文档
```

### 代码规模

| 指标 | 数值 |
|------|------|
| Python 文件 | 8 个 |
| Docker | ✅ |
| 注册方式 | SkillPlugin（`@register_skill`） |

---

## 六、Spider-X（扩展适配层）

**当前版本：未标注 | 状态：开发中**

spider_meta 的**扩展层**，第三方 API 适配、自定义协议。

### 代码规模

| 指标 | 数值 |
|------|------|
| Python 文件 | 42 个 |
| Docker | ❌ |
| 注册方式 | SkillPlugin（`@register_skill`） |

---

## 生态总览

```
                   ┌─────────────────────────────┐
                   │       spider_meta v0.5.0      │
                   │    控制平面 · 元智能体编排      │
                   │   进度 80% · 52 测试通过       │
                   └──────────────┬────────────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
     ┌────────▼────────┐  ┌──────▼──────┐  ┌────────▼────────┐
     │  执行层          │  │  经验层      │  │  扩展层          │
     │                 │  │             │  │                 │
     │ mini_spider     │  │spider_diary │  │  Spider-X       │
     │ v1.0.0 ✅已上线  │  │ v1.0.0 开发中│  │ 版本未定 开发中   │
     │ Worker 注册     │  │ Tool 注册   │  │ SkillPlugin 注册 │
     │                 │  │             │  │                 │
     │ spider_max      │  │             │  │ spidermax_room  │
     │ v3.0.0 ✅已上线  │  │             │  │ v2.0.0 ✅已上线  │
     │ Worker 注册     │  │             │  │ SkillPlugin 注册 │
     └─────────────────┘  └─────────────┘  └─────────────────┘
```

### 注册机制对照

| 子项目 | 注册方式 | spider_meta 调它做什么 |
|--------|---------|---------------------|
| mini_spider | `POST /workers/register` | 爬取网页、数据采集 |
| spider_max | `POST /workers/register` | 大规模爬取、JS渲染、反爬 |
| spider_diary | `tools.register()` | 日志存储、经验查询 |
| Spider-X | `@register_skill` | 第三方 API 适配 |
| spidermax_room | `@register_skill` | 多 Agent 协作空间 |

### 健康状态

| 项目 | 版本 | 进度 | 健康分 | Docker | CI/CD |
|------|------|------|--------|--------|-------|
| spider_meta | v0.5.0 | 80% | 80 | ✅ | ✅ |
| spider_max | v3.0.0 | 100% | 92 | ✅ | ❌ |
| mini_spider | v1.0.0 | 100% | 85 | ❌ | ❌ |
| spider_diary | v1.0.0 | ~70% | — | ✅ | ❌ |
| spidermax_room | v2.0.0 | 100% | — | ✅ | ❌ |
| Spider-X | 未定 | ~50% | — | ❌ | ❌ |
