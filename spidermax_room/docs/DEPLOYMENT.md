# DEPLOYMENT — MAX ROOM Docker 部署指南

## 前置条件

- Docker Desktop（Windows）或 Docker Engine（Linux）
- Docker Compose v2+

## 快速部署

### 1. 构建镜像

```bash
cd E:\软件开发\spidermax_room
docker build -t spidermax-room:2.0.0 .
```

构建过程中会自动运行测试。如果测试失败，构建会中止。

### 2. 运行容器

```bash
# 交互式（进入 Python 解释器）
docker run -it --rm spidermax-room:2.0.0

# 后台运行
docker run -d --name max-room spidermax-room:2.0.0

# 查看日志
docker logs max-room

# 进入运行中的容器
docker exec -it max-room python
```

### 3. 验证

```bash
# 交互式验证
docker run -it --rm spidermax-room:2.0.0 python -c "
from spidermax_room import RoomEngine, Member, MemberRole

engine = RoomEngine()
room = engine.create_room('test')
room.join(Member('alice'))
room.join(Member('bob'))
room.broadcast('alice', {'content': 'Docker works!'})

print(f'Room: {room.name}')
print(f'Members: {room.member_count}')
print(f'Events: {len(room.history)}')
print('All OK!')
"
```

---

## Docker Compose 方式（推荐）

### 启动服务

```bash
docker compose up -d
```

### 查看状态

```bash
docker compose ps
docker compose logs -f
```

### 进入交互式 Python 环境

```bash
docker compose run --rm max-room
```

### 运行完整测试

```bash
docker compose --profile test run --rm max-room-test
```

### 停止并清理

```bash
docker compose down
docker compose down -v  # 同时删除持久化数据
```

---

## 作为 Python 库使用

### 从宿主机构建中导入

```bash
# 挂载本地代码到容器（开发模式）
docker run -it --rm -v %cd%:/app spidermax-room:2.0.0 python
```

### 在其他项目中引用

```python
# requirements.txt
spidermax-room @ git+https://github.com/freeword26/Mini-spider.git#subdirectory=spidermax_room
```

---

## 镜像信息

| 属性 | 值 |
|------|-----|
| 基础镜像 | python:3.12-slim |
| 工作目录 | /app |
| 暴露端口 | 无（纯库，无网络服务） |
| 数据卷 | /app/logs |
| 资源限制 | CPU 0.5核 / 内存 256MB |
| 健康检查 | 每 30 秒验证包可导入 |

## 常见问题

**Q: 构建失败，提示测试未通过？**
A: 本地先运行 `pytest tests/ -v` 修复测试，再重新构建。

**Q: 容器启动后立即退出？**
A: 正常运行（库不需要常驻进程）。如需交互模式加 `-it` 参数。

**Q: 如何使用最新版？**
A: 重新构建镜像：`docker build --no-cache -t spidermax-room:2.0.0 .`
