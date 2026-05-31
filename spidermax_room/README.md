# spidermax_room — MAX ROOM

> **虚拟协作空间：让 AI Agent 和人一起开会、沟通、协作**

MAX ROOM 是一个"会议室"系统。你可以创建房间，让成员（人或 AI Agent）加入，发消息、听事件、追踪状态。就像 Zoom 会议室或 Discord 频道，但是给程序用的。

---

## 30 秒上手

```bash
# 安装
cd E:\软件开发\spidermax_room
pip install -e .

# 运行测试，确认一切正常
pytest tests/ -v
```

```python
from spidermax_room import RoomEngine, Room, Member, MemberRole

# 1. 创建一个引擎（管理多个房间）
engine = RoomEngine()

# 2. 开一个房间
room = engine.create_room("daily-standup")

# 3. 成员加入
room.join(Member("pm", role=MemberRole.FACILITATOR))
room.join(Member("dev-1"))
room.join(Member("dev-2"))

# 4. 聊天
room.broadcast("pm", {"content": "晨会开始，昨天做了什么？"})
room.send_to("dev-1", "dev-2", {"content": "我负责前端"})

# 5. 听所有事件
room.on_event(lambda e: print(f"[{e.sender}] {e.type.value}: {e.data}"))

# 6. 查看房间状态
print(room.member_count)     # 3
print(engine.status())       # 所有房间概览

# 7. 散会
engine.destroy_room("daily-standup")
```

---

## 核心模块

### Room（房间）

一个成员可以**加入/离开**、能**广播消息**的协作空间。

| 操作 | 方法 | 返回值 |
|------|------|--------|
| 成员加入 | `room.join(Member("alice"))` | RoomEvent |
| 成员离开 | `room.leave("alice")` | RoomEvent |
| 广播消息 | `room.broadcast("alice", {"content": "hi"})` | RoomEvent |
| 私信 | `room.send_to("alice", "bob", {"content": "hey"})` | RoomEvent |
| 状态变更 | `room.set_status("alice", MemberStatus.AWAY)` | RoomEvent |
| 查看成员 | `room.members` / `room.get_member("alice")` | Member |
| 谁在房间 | `room.member_count` | int |
| 事件历史 | `room.history` | list[RoomEvent] |

**事件驱动：** 房间里发生的每件事都是一个事件。用 `on_event()` 注册监听器，收到通知：

```python
# 监听所有事件
room.on_event(lambda e: print(e))

# 只监听消息事件
room.on_event(lambda e: print(e.data), event_type=EventType.MESSAGE)

# 只监听成员加入
room.on_event(new_member_handler, EventType.MEMBER_JOINED)
```

### Member（成员）

房间里的参与者，有**角色**和**状态**：

```python
from spidermax_room import Member, MemberRole, MemberStatus

# 创建成员
pm   = Member("pm",   role=MemberRole.FACILITATOR)  # 主持人
dev  = Member("dev",  role=MemberRole.PARTICIPANT)  # 参与者
bot  = Member("bot",  role=MemberRole.OBSERVER)     # 观察者（只看不说话）

# 状态
alice = Member("alice", status=MemberStatus.ONLINE)   # 在线
bob   = Member("bob",   status=MemberStatus.AWAY)     # 离开
carol = Member("carol", status=MemberStatus.OFFLINE)  # 离线
```

### EventType（事件类型）

房间里可能发生的事件：

| 事件 | 含义 |
|------|------|
| `MEMBER_JOINED` | 有人加入房间 |
| `MEMBER_LEFT` | 有人离开房间 |
| `MEMBER_STATUS_CHANGED` | 有人状态改变（在线→离开） |
| `MESSAGE` | 有人发消息（广播或私信） |
| `WHITEBOARD_UPDATE` | 白板内容更新（扩展） |
| `DOCUMENT_SHARED` | 有人分享文档（扩展） |
| `TASK_UPDATED` | 任务状态变更（扩展） |
| `CUSTOM` | 自定义事件（扩展） |

### RoomEngine（引擎）

管理多个房间的"管理员"：

```python
engine = RoomEngine()

# 创建房间
standup = engine.create_room("daily-standup")
sprint  = engine.create_room("sprint-planning")

# 查看状态
print(engine.room_count)    # 2
print(engine.room_names)    # ["daily-standup", "sprint-planning"]
print(engine.status())      # 全部房间概览

# 获取已有房间
room = engine.get_room("daily-standup")

# 销毁房间
engine.destroy_room("daily-standup")
print(engine.room_count)    # 1
```

---

## 完整示例：Sprint 评审会议

```python
from spidermax_room import *

# 创建引擎和房间
engine = RoomEngine()
room = engine.create_room("sprint-review")

# 事件日志：记录房间里发生的所有事
def log_event(event):
    print(f"  [{event.type.value}] {event.sender}: {event.data}")

room.on_event(log_event)

# 成员加入
print("=== 成员加入 ===")
room.join(Member("pm",      role=MemberRole.FACILITATOR))
room.join(Member("dev-1",   role=MemberRole.PARTICIPANT))
room.join(Member("dev-2",   role=MemberRole.PARTICIPANT))
room.join(Member("qa-bot",  role=MemberRole.OBSERVER))

print(f"房间里有 {room.member_count} 人")

# 会议开始
print("\n=== PM 发言 ===")
room.broadcast("pm", {"content": "Sprint 评审开始，请各组汇报"})

# 开发汇报
print("\n=== 开发汇报 ===")
room.broadcast("dev-1", {"content": "前端：完成了登录页面和用户中心"})
room.broadcast("dev-2", {"content": "后端：完成了 API 网关和数据库迁移"})

# 私下沟通
print("\n=== 私下沟通 ===")
room.send_to("dev-1", "dev-2", {"content": "API 文档我看一下"})

# 有人离开
print("\n=== dev-2 离开 ===")
room.set_status("dev-2", MemberStatus.AWAY)
room.leave("dev-2")

# 汇总
print(f"\n=== 会议结束 ===")
print(f"最终房间人数: {room.member_count}")
print(f"总事件数: {len(room.history)}")

# 回顾所有事件
for i, event in enumerate(room.history, 1):
    print(f"  {i}. {event}")

# 清理
engine.destroy_room("sprint-review")
print(f"引擎房间数: {engine.room_count}")  # 0
```

**输出：**
```
=== 成员加入 ===
  [member_joined] pm: {'member': Member(pm, role=facilitator, status=online)}
  [member_joined] dev-1: ...
  [member_joined] dev-2: ...
  [member_joined] qa-bot: ...
房间里有 4 人

=== PM 发言 ===
  [message] pm: {'content': 'Sprint 评审开始，请各组汇报'}
...
```

---

## 项目结构

```
spidermax_room/
│
├── 源码（核心模块）
│   ├── room.py       # Room — 房间：成员管理 + 消息 + 事件
│   ├── member.py     # Member / MemberRole / MemberStatus — 参与者
│   ├── event.py      # RoomEvent / EventType — 事件与事件类型
│   └── engine.py     # RoomEngine — 引擎：管理多个房间
│
├── __init__.py       # 统一导出所有公开接口
│
├── 测试
│   └── tests/
│       └── test_version.py  # 17 个测试，覆盖所有功能
│
├── 文档
│   ├── docs/architecture.md   # 架构设计
│   ├── docs/api.md            # API 参考
│   └── docs/user-guide.md     # 用户指南
│
├── 项目配置
│   ├── pyproject.toml   # 包配置、pytest 设置
│   ├── metadata.json    # 项目元数据（版本、进度等）
│   └── .gitignore
│
└── GitHub 标准文件
    ├── LICENSE              # MIT 许可证
    ├── CHANGELOG.md         # 变更日志
    ├── CONTRIBUTING.md      # 贡献指南
    ├── SECURITY.md          # 安全策略
    ├── CODE_OF_CONDUCT.md   # 行为准则
    └── .github/             # Issue/PR 模板
```

---

## 开发与测试

```bash
# 安装（开发模式）
pip install -e .

# 运行测试
pytest tests/ -v

# 测试应该输出 17 passed
```

## 设计思路

```
RoomEngine（管理员）
    ├── Room "daily-standup"（房间 A）
    │     ├── Member: pm, dev-1, dev-2（成员）
    │     ├── broadcast() → 所有人收到消息
    │     ├── send_to()   → 私信某个人
    │     └── on_event()  → 监听所有事件类型
    │
    └── Room "sprint-planning"（房间 B）
          ├── Member: pm, dev-1, qa-bot
          └── ...

每个 Room 独立运作，互不干扰。
所有交互通过事件驱动——发生任何事，订阅者都会收到通知。
```

## 未来扩展（Backlog）

- `WHITEBOARD_UPDATE` — 多人协作白板
- `DOCUMENT_SHARED` — 文档协同编辑
- `TASK_UPDATED` — 看板任务同步
- 持久化：房间状态保存到数据库
- WebSocket 支持：实时网络通信

## License

[MIT](LICENSE)
