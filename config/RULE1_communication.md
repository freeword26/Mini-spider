# 规则一：多智能体架构与通信规范

> 适用对象：系统经理Agent、LangChain协同编排Agent、API网关  
> 核心目标：确保19个Agent节点的松耦合、高内聚及消息总线的稳定性。

---

## 1. 消息总线强制协议

### 1.1 标准化信封
所有通过消息总线传递的数据**必须**封装在统一的 `AgentMessage` Schema 中：

| 字段 | 类型 | 说明 |
|------|------|------|
| `sender_id` | `str` | 发送者 Agent ID |
| `receiver_id` | `str` | 接收者 Agent ID（`*` 表示广播） |
| `session_id` | `str` | 会话链ID，追踪同一次会话 |
| `message_id` | `str` | 消息唯一ID |
| `priority` | `int` (1-5) | 优先级（5最高） |
| `timestamp` | `str` (ISO8601) | 消息创建时间戳 |
| `payload` | `dict` | 消息内容体 |
| `trace_id` | `str` | 全链路追踪ID |
| `error` | `dict \| None` | 错误信息 |

### 1.2 发布/订阅隔离
- Agent **严禁**直接点对点调用
- 必须通过 `MessageBroker`（RabbitMQ/Kafka/内存队列）进行解耦
- Agent A 只负责**发布事件**，不关心谁消费
- 消费者通过订阅事件类型接收消息

### 1.3 死信队列
- 所有无法被路由或处理失败的消息**必须**进入死信队列
- 死信队列到达阈值（如10条/分钟）时触发 `SystemManager` 警报

---

## 2. 协同编排逻辑约束

### 2.1 单向指挥链
```
System Manager
    └──> LangChain Orchestrator
            └──> Skill-Specific Agents
```
- **严禁**底层Agent反向控制编排层
- 底层Agent只能通过事件上报状态，不可调用编排层API

### 2.2 编排模式声明
在 `MultiAgentOrchestrator` 配置中，必须显式声明协作模式：

| 模式 | 适用场景 | 说明 |
|------|----------|------|
| `DAG` | 线性任务流 | 有严格依赖关系，按拓扑序执行 |
| `Blackboard` | 复杂问题求解 | 共享上下文黑板，多Agent协同贡献 |
| `PMO` | 项目执行 | 项目经理主导，顺序执行 |
| `SOP` | 标准化流程 | 严格步骤，每个步骤有明确输入输出 |

### 2.3 负载均衡
- API网关层必须启用轮询（Round Robin）或加权路由
- 确保19个执行节点的CPU/内存资源利用率均衡（偏差 < 20%）

---

## 3. 异常熔断机制

### 3.1 超时熔断
- 单个Agent处理时间超过阈值（默认 **30秒**）自动熔断
- 触发 `FallbackStrategy`（如切换到备用Agent）
- 连续3次超时则标记该Agent为 `unhealthy`，停止分发

### 3.2 错误传播
- 子Agent报错时，**必须**封装为 `ErrorEvent` 广播
- **严禁**让整个编排链路因单点故障而静默失败
- 错误事件包含：`agent_id`, `task_id`, `error_type`, `stack_trace`, `timestamp`

---

## 4. 代码实现要求

| 检查项 | 达标标准 | 负责人 |
|--------|----------|--------|
| 消息格式 | 100% 符合 AgentMessage Schema | System Manager |
| 通信方式 | 无直接点对点调用 | LangChain Orchestrator |
| 心跳检测 | 每30秒发送，3次未收到标记离线 | All Agents |
| 超时熔断 | 30秒超时自动熔断 | API Gateway |
| 错误广播 | ErrorEvent 覆盖所有异常场景 | All Agents |

---

## 5. 元系统集成

> 本规则受 `.rules/self_healing_rules.md` (L0根规则) 管辖  
> 协议版本统一由 `registry.yaml` 注册  
> 版本冲突由 Architect-Agent 批量升级