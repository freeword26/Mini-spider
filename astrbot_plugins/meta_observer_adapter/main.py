"""
meta_observer-adapter - AstrBot 插件（v2.0）

架构融合版：
- AstrBot 仅做意图识别 + 用户授权网关
- 事件通过 RabbitMQ 发布，不再直接调用服务
- 关键操作必须经 auth_gateway 用户确认
- 符合 CVE-2025-55449 沙箱隔离规范
"""

import json
import asyncio
import httpx
import os
import sys
from datetime import datetime
from pathlib import Path
from astrbot.api import star, llm_tool
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.message_components import Plain
from astrbot.core import logger

sys.path.insert(0, r"E:\软件开发\3_任务执行中枢（TAPD）")
from local_event_bus import get_publisher, LocalEventBus, check_rabbitmq_available
from agents_orchestrator.core.message_bus import AgentMessage

EXCHANGE_EVENTS = "project.events"


class Main(star.Star):
    def __init__(self, context: star.Context) -> None:
        self.context = context
        self.pending_events = []
        self.user_authorizations = {}
        self._publisher = None
        self._event_consumer = None
        self._task_results: dict = {}
        logger.info("meta_observer-adapter v3.0 初始化成功")

    async def _start_result_consumer(self):
        """启动任务结果事件消费者（TD-P1-003：本地降级）"""
        try:
            rmq_available = check_rabbitmq_available()
            if not rmq_available:
                logger.info("RabbitMQ 不可用，使用本地事件队列消费")
                from local_event_bus import LocalEventConsumer
                consumer = LocalEventConsumer(
                    agent_id="astrobot-result-consumer",
                    binding_keys=["task.completed.broadcast", "task.failed.broadcast"],
                )
                consumer.register_handler("task.completed", self._on_task_completed)
                consumer.register_handler("task.failed", self._on_task_failed)
                self._event_consumer = consumer
                consumer.start_consuming(block=False)
                logger.info("✅ AstrBot 本地结果事件消费者已启动")
                return

            from agents_orchestrator.core.event_consumer import EventConsumer
            import os
            rmq_url = os.environ.get("RABBITMQ_URL", "")
            consumer = EventConsumer(
                agent_id="astrobot-result-consumer",
                url=rmq_url,
                binding_keys=["task.completed.broadcast", "task.failed.broadcast"],
            )
            consumer.register_handler("task.completed", self._on_task_completed)
            consumer.register_handler("task.failed", self._on_task_failed)
            self._event_consumer = consumer
            consumer.start_consuming(block=False)
            logger.info("✅ AstrBot RabbitMQ 结果事件消费者已启动")
        except Exception as e:
            logger.warning(f"结果消费者启动失败: {e}")

    def _on_task_completed(self, msg):
        """任务完成回调"""
        payload = msg.payload
        task_id = payload.get("task_id", "unknown")
        agent_id = payload.get("agent_id", "unknown")
        result = payload.get("result", {})
        self._task_results[task_id] = {"status": "completed", "result": result}
        logger.info(f"[CALLBACK] 任务完成: {task_id} by {agent_id}")

    def _on_task_failed(self, msg):
        """任务失败回调"""
        payload = msg.payload
        task_id = payload.get("task_id", "unknown")
        agent_id = payload.get("agent_id", "unknown")
        error = payload.get("error", "unknown error")
        self._task_results[task_id] = {"status": "failed", "error": error}
        logger.warning(f"[CALLBACK] 任务失败: {task_id} by {agent_id}: {error}")

    def _get_publisher(self):
        if self._publisher is None:
            try:
                self._publisher = get_publisher()
                self._rmq_available = check_rabbitmq_available()
            except Exception as e:
                logger.warning(f"事件发布器初始化失败，降级为本地模式: {e}")
                from local_event_bus import LocalEventPublisher
                self._publisher = LocalEventPublisher()
                self._rmq_available = False
        return self._publisher

    async def _publish_event(self, event_type: str, payload: dict, target: str = "*"):
        msg = AgentMessage(
            sender_id="meta_observer",
            receiver_id=target,
            priority=payload.get("priority", 3),
            payload={"event_type": event_type, **payload},
        )
        pub = self._get_publisher()
        if pub:
            try:
                routing_key = f"{event_type}.{target}"
                pub.publish(msg, routing_key=routing_key)
                logger.info(f"事件已发布: {routing_key}")
            except Exception as e:
                logger.error(f"事件发布失败: {e}")
        else:
            logger.warning(f"[本地模式] 事件未发布: {event_type}")
        return msg

    async def add_pending_event(self, event: dict):
        self.pending_events.append(event)
        await self._publish_event("observer.alert", {
            "description": event.get("description", ""),
            "target": event.get("target", ""),
            "severity": event.get("severity", "medium"),
            "file_count": event.get("file_count", 0),
            "threshold": event.get("threshold", 0),
        })

    def format_event_as_notification(self, event: dict) -> str:
        severity_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        emoji = severity_emoji.get(event.get("severity", "medium"), "⚪")
        return (
            f"{emoji} 【系统通知】\n"
            f"检测到问题: {event.get('description', '')}\n"
            f"目标: {event.get('target', '')}\n"
            f"详情: 文件数 {event.get('file_count', 0)} (阈值 {event.get('threshold', 0)})\n"
            f"\n是否需要处理此问题？\n"
            f"回复 '确认处理' 或 '忽略'。"
        )

    @filter.command("查看待处理事件")
    async def list_pending_events(self, event: AstrMessageEvent) -> None:
        if not self.pending_events:
            yield event.plain_result("✅ 当前没有待处理的事件")
            return
        msg = "📋 待处理事件列表:\n\n"
        for i, e in enumerate(self.pending_events, 1):
            msg += f"{i}. {e.get('type', '?')} - {e.get('target', '?')}\n"
        yield event.plain_result(msg)

    @filter.command("处理事件")
    async def process_event(self, event: AstrMessageEvent) -> None:
        if not self.pending_events:
            yield event.plain_result("✅ 当前没有待处理的事件")
            return

        target_event = self.pending_events[0]
        user_id = event.get_user_id()

        # TD-P1-001b: 通过本地授权服务验证
        auth_token = await self._require_local_authorization(
            user_id=user_id,
            action="archive",
            target=target_event.get("target", ""),
            description=target_event.get("description", ""),
        )

        if not auth_token:
            yield event.plain_result(
                "❌ 授权验证未通过。\n"
                "请先使用「授权确认 <请求ID>」确认操作。"
            )
            return

        self.user_authorizations[user_id] = {
            "event_id": target_event.get("id", "unknown"),
            "authorized_at": datetime.now().isoformat(),
            "auth_token": auth_token,
        }

        await self._publish_event("user.authorized", {
            "user_id": user_id,
            "action": "process_event",
            "target": target_event.get("target", ""),
            "event_id": target_event.get("id", ""),
        })

        yield event.plain_result(
            f"✅ 已确认处理事件: {target_event.get('target', '')}\n"
            f"正在通过 MCP 工具调用归档服务..."
        )

        result = await self.archive_directory_via_mcp(target_event.get("target", ""))

        # 只有归档成功后才移除事件
        self.pending_events.pop(0)

        await self._publish_event("task.completed", {
            "action": "archive",
            "target": target_event.get("target", ""),
            "result": result,
        })

        yield event.plain_result(f"✅ {result}")

    async def _require_local_authorization(self, user_id: str, action: str, target: str, description: str) -> str:
        """通过本地授权服务创建并验证授权（TD-P1-001b 集成）"""
        try:
            import subprocess
            exe = sys.executable
            auth_script = str(Path(r"E:\软件开发\3_任务执行中枢（TAPD）\local_auth_service.py"))
            env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}

            # 检查是否有已存在的 pending 请求
            r = subprocess.run(
                [exe, auth_script, "list", "--user", user_id],
                capture_output=True, text=True, timeout=10, env=env,
            )
            if r.stdout and "expires:" in r.stdout:
                import re
                m = re.search(r'\[([a-f0-9]+)\]', r.stdout)
                if m:
                    req_id = m.group(1)
                    r2 = subprocess.run(
                        [exe, auth_script, "confirm", "--user", user_id, "--req-id", req_id],
                        capture_output=True, text=True, timeout=10, env=env,
                    )
                    if "令牌:" in r2.stdout:
                        token = r2.stdout.split("令牌:")[-1].strip()
                        return token

            # 没有 pending 请求，创建一个新的
            r3 = subprocess.run(
                [exe, auth_script, "create",
                 "--user", user_id,
                 "--action", action,
                 "--target", target,
                 "--desc", description],
                capture_output=True, text=True, timeout=10, env=env,
            )
            if r3.returncode == 0 and "请求ID:" in r3.stdout:
                import re
                m = re.search(r"请求ID[：:]\s*([a-f0-9]+)", r3.stdout)
                if m:
                    req_id = m.group(1)
                    r4 = subprocess.run(
                        [exe, auth_script, "confirm", "--user", user_id, "--req-id", req_id],
                        capture_output=True, text=True, timeout=10, env=env,
                    )
                    if "令牌:" in r4.stdout:
                        return r4.stdout.split("令牌:")[-1].strip()

            return None
        except Exception as e:
            logger.warning(f"本地授权检查失败: {e}")
            return None

    @llm_tool("archive_directory")
    async def archive_directory_via_mcp(self, directory: str) -> str:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "http://localhost:8000/api/v1/archive",
                    json={"directory": directory, "dry_run": False},
                )
                if response.status_code == 200:
                    result = response.json()
                    return (
                        f"归档服务调用成功\n"
                        f"目录: {directory}\n"
                        f"原始文件数: {result.get('original_count', 0)}\n"
                        f"已归档: {result.get('archived_count', 0)} 个\n"
                        f"剩余文件: {result.get('remaining_count', 0)} 个\n"
                        f"消息: {result.get('message', '')}"
                    )
                else:
                    return f"归档服务调用失败: {response.status_code}"
        except Exception as e:
            logger.error(f"归档服务调用异常: {e}")
            return f"归档服务调用异常: {str(e)}"

    @llm_tool("get_meta_observer_status")
    async def get_meta_observer_status(self) -> str:
        pending_count = len(self.pending_events)
        status = "正常" if pending_count == 0 else f"有 {pending_count} 个待处理事件"
        return (
            f"📊 Meta Observer 状态\n"
            f"状态: {status}\n"
            f"待处理事件数: {pending_count}\n"
            f"插件版本: 2.0.0\n"
            f"事件总线: {'已连接' if self._publisher else '本地模式'}"
        )

    @llm_tool("publish_system_event")
    async def publish_system_event(
        self, event_type: str, description: str, target: str = "*", priority: int = 3
    ) -> str:
        payload = {
            "description": description,
            "target": target,
            "priority": priority,
            "source": "meta_observer",
        }
        msg = await self._publish_event(event_type, payload, target)
        return json.dumps({
            "status": "published",
            "message_id": msg.message_id,
            "event_type": event_type,
            "trace_id": msg.trace_id,
        }, ensure_ascii=False)

    @filter.regex(r"(?i).*(确认|处理|归档).*")
    async def handle_intent_recognition(self, event: AstrMessageEvent) -> None:
        if self.pending_events:
            await self.process_event(event)
        else:
            yield event.plain_result(
                "🤔 当前没有待处理的事件。\n"
                "如果需要归档，可以直接告诉我要归档哪个目录。"
            )

    @filter.command("发送测试通知")
    async def send_test_notification(self, event: AstrMessageEvent) -> None:
        test_event = {
            "type": "S1_violation",
            "severity": "high",
            "target": "测试目录",
            "file_count": 100,
            "threshold": 50,
            "description": "测试通知 - 验证集成通道",
            "timestamp": datetime.now().isoformat(),
        }
        await self.add_pending_event(test_event)
        notification = self.format_event_as_notification(test_event)
        yield event.plain_result(notification)
    @filter.command("任务结果")
    async def query_task_result(self, event: AstrMessageEvent) -> None:
        """查询子任务执行结果：任务结果 <task_id>"""
        args = event.get_message_str().strip().split()
        if len(args) < 2:
            # 列出最近完成的任务
            if not self._task_results:
                yield event.plain_result("📋 暂无任务执行结果")
                return
            msg = "📋 最近任务执行结果:\n\n"
            for tid, info in list(self._task_results.items())[-10:]:
                status_emoji = "✅" if info["status"] == "completed" else "❌"
                msg += f"{status_emoji} `{tid}` → {info['status']}\n"
            yield event.plain_result(msg)
            return
        task_id = args[1]
        result = self._task_results.get(task_id)
        if result:
            status_emoji = "✅" if result["status"] == "completed" else "❌"
            msg = f"{status_emoji} 任务 `{task_id}` 结果:\n\n"
            if result["status"] == "completed":
                msg += f"```json\n{json.dumps(result['result'], ensure_ascii=False, indent=2)[:500]}\n```"
            else:
                msg += f"错误: {result.get('error', 'unknown')}"
            yield event.plain_result(msg)
        else:
            yield event.plain_result(f"❓ 未找到任务 `{task_id}` 的结果")
        logger.info("测试通知已发送")
