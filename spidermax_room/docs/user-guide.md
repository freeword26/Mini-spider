# MAX ROOM 使用说明

## 是什么？

MAX ROOM 是一个**虚拟协作空间**。你可以：
- 创建房间
- 让成员（人或 AI Agent）加入
- 发广播消息或私信
- 监听房间里发生的任何事
- 管理多个房间

类比：就像 Zoom 会议室 + Discord 频道 + 事件总线，三合一。

---

## 安装

```bash
cd E:\软件开发\spidermax_room
pip install -e .
```

---

## 快速上手

### 1. 创建引擎和房间

```python
from spidermax_room import RoomEngine, Room, Member, MemberRole

engine = RoomEngine()
room = engine.create_room("my-room")
```

### 2. 成员加入

```python
room.join(Member("alice"))
room.join(Member("bob", role=MemberRole.FACILITATOR))
room.join(Member("charlie", role=MemberRole.OBSISTANT))
```

### 3. 发消息

```python
# 广播给所有人
room.broadcast("alice", {"content": "大家好！"})

# 私信给某个人
room.send_to("alice", "bob", {"content": "私聊内容"})
```

### 4. 监听事件

```python
# 方式一：处理所有事件
room.on_event(lambda e: print(f"[{e.sender}] {e.type.value}"))

# 方式二：只处理特定事件
room.on_event(lambda e: print(e.data), EventType.MESSAGE)
```

### 5. 查看状态

```python
room.member_count          # 当前有几人
room.members               # 所有成员
room.get_member("alice")   # 查看某个成员（返回 None 表示不在房间）
room.history               # 所有历史事件
engine.status()            # 所有房间概览
```

### 6. 成员离开 / 散会

```python
room.leave("alice")                     # 某人离开
room.set_status("bob", MemberStatus.AWAY)  # 状态改为离开
engine.destroy_room("my-room")          # 销毁房间
```

---

## 完整场景演示

场景：三个 AI Agent 开一个 Sprint Planning 会议。

```python
from spidermax_room import *

# 初始化
engine = RoomEngine()
room = engine.create_room("sprint-planning")

# 事件监控
room.on_event(lambda e: print(f"  → {e.type.value}: {e.sender}"))

# 成员加入
print("成员加入:")
room.join(Member("pm",       role=MemberRole.FACILITATOR))
room.join(Member("frontend", role=MemberRole.PARTICIPANT))
room.join(Member("backend",  role=MemberRole.PARTICIPANT))

# PM 发起讨论
print("\nPM 发言:")
room.broadcast("pm", {"content": "开始 Sprint Planning，请各组报告排期"})

# 各组报告
print("\n各组报告:")
room.broadcast("frontend", {"content": "本周完成用户登录和权限管理"})
room.broadcast("backend",  {"content": "本周完成 API 网关和数据库优化"})

# 私下沟通
print("\n私下沟通:")
room.send_to("frontend", "backend", {"content": "API 文档发我一下"})

# 某人临时离开
print("\nBackend 暂时离开:")
room.set_status("backend", MemberStatus.AWAY)

# 查看最终状态
print(f"\n总结:")
print(f"  房间: {room.name}")
print(f"  人数: {room.member_count}")
print(f"  事件: {len(room.history)} 条")
for name, m in room.members.items():
    print(f"    {name}: {m.role.value}, {m.status.value}")

# 散会
engine.destroy_room("sprint-planning")
print(f"\n引擎房间数: {engine.room_count}")  # 0
```

---

## 何时使用什么

| 需求 | 用哪个 |
|------|--------|
| 管理多个房间（创建/销毁） | `RoomEngine` |
| 让人进入/离开协作空间 | `Room.join()` / `Room.leave()` |
| 群里发消息 | `Room.broadcast()` |
| 悄悄话 | `Room.send_to()` |
| 监控房间里的所有动态 | `Room.on_event()` |
| 只看特定类型的事件 | `Room.on_event(handler, EventType.MESSAGE)` |
| 查看回放 | `Room.history` |
| 看谁在房间里 | `Room.members` / `Room.member_count` |

---

## 运行测试

```bash
pytest tests/ -v
# 期望输出: 17 passed
```
