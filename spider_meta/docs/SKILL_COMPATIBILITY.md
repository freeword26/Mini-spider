# 注册机制说明

spider_meta 提供 **4 种注册方式**，对应 5 个 Spider 生态子项目。

## 注册方式速查

| 方式 | 适用项目 | 注册方法 | 效果 |
|------|---------|---------|------|
| Worker 注册 | mini_spider, spider_max | `POST /workers/register` | 自动技能匹配、负载均衡、心跳保活 |
| Tool 注册 | spider_diary, 外部 API | `tools.register(name, func)` | 作为工具出现在 `/tools` 列表中 |
| SkillPlugin 注册 | Spider-X, spidermax_room | `@register_skill` 装饰器 | 同时注册为插件 + 工具（自动联动） |
| Event 订阅 | 所有项目 | `event_bus.subscribe()` | 事件驱动自动化 |

---

## 方式一：Worker 注册

**端点**: `POST /workers/register`  
**代码位置**: `main.py` → `dispatcher.register_worker()` → `core/worker_dispatcher.py`

```bash
# mini_spider 注册
curl -X POST http://localhost:8003/workers/register \
  -H "Content-Type: application/json" \
  -d '{"worker_id":"mini-01","skills":["crawl","parse"],"endpoint":"http://mini:8001"}'

# 查看已注册 Worker
curl http://localhost:8003/workers

# 注销 Worker
curl -X DELETE http://localhost:8003/workers/mini-01
```

## 方式二：Tool 注册

**入口**: `main.py` → `tools.register()`  
**代码位置**: `main.py` → `ToolRegistry`

```python
from spider_meta.main import tools

async def my_api(query: str) -> dict:
    return {"result": f"processed: {query}"}

tools.register("my_api", my_api, "我的 API 工具", {"query": "string"})
```

## 方式三：SkillPlugin 注册（自动联动工具）

**入口**: `@register_skill` 装饰器  
**代码位置**: `plugins/__init__.py` → `PluginRegistry`

注册后会**同时**出现在 PluginRegistry 和 ToolRegistry（自动联动在 `main.py` 第108行绑定）。

```python
from spider_meta.plugins import SkillPlugin, register_skill

@register_skill
class MySkill(SkillPlugin):
    name = "my_skill"
    version = "1.0.0"
    description = "我的技能"
    def activate(self, ctx): pass
    async def execute(self, task):
        return {"status": "done"}
```

## 方式四：Event 订阅

**入口**: `event_bus.subscribe()`  
**代码位置**: `core/event_bus.py`

```python
from spider_meta.core.event_bus import event_bus, EventType

async def on_complete(event):
    print(f"任务完成: {event.data}")

event_bus.subscribe([EventType.TASK_COMPLETED], on_complete)
```

## 注册后的调度流程

```
子项目注册 → spider_meta 接收 → 存储到对应的 Registry
                                    ↓
用户提交任务 → Pipeline 拆解 → 技能匹配 → 分配执行 → 结果汇总
                                    ↑
                              查询 Registry
```
