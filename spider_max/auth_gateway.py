#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户授权网关 — 三层闭环架构冲突#6解决方案
所有关键操作必须经过用户确认，超时默认拒绝（安全优先）
"""

import uuid
import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class AuthorizationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    TIMEOUT = "timeout"


@dataclass
class AuthorizationRequest:
    request_id: str
    action: str
    description: str
    agent_id: str
    target: str
    status: AuthorizationStatus = AuthorizationStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    responded_at: Optional[str] = None
    authorized_by: Optional[str] = None


CRITICAL_OPERATIONS = {
    "file_archive": "归档文件至永久存储 — 不可逆操作",
    "tech_debt_register": "注册技术债务 — 影响项目质量评估",
    "delete_file": "删除文件 — 不可逆操作",
    "config_modify": "修改系统配置 — 影响运行行为",
    "database_migrate": "数据库迁移 — 影响数据结构",
    "service_restart": "重启服务 — 影响可用性",
    "deployment": "生产部署 — 影响用户",
    "permission_change": "权限变更 — 影响安全边界",
}

COMPOUND_OPERATIONS = {
    "archive_and_delete": ["file_archive", "delete_file"],
    "config_and_restart": ["config_modify", "service_restart"],
    "migrate_and_deploy": ["database_migration", "deployment"],
}


class UserAuthorizationManager:
    """用户授权管理 — 所有关键操作必须经过确认"""

    def __init__(
        self,
        event_bus=None,
        default_timeout: int = 300,
        approval_callback=None,
    ):
        self.event_bus = event_bus
        self.default_timeout = default_timeout
        self.approval_callback = approval_callback
        self._pending_requests: Dict[str, AuthorizationRequest] = {}
        self._approved_history: List[AuthorizationRequest] = []

    def requires_authorization(self, action: str) -> bool:
        return action in CRITICAL_OPERATIONS

    def create_authorization_request(
        self,
        action: str,
        agent_id: str,
        target: str,
        description: str = "",
        timeout: Optional[int] = None,
    ) -> AuthorizationRequest:
        if action not in CRITICAL_OPERATIONS:
            auto_req = AuthorizationRequest(
                request_id=f"auto_{uuid.uuid4().hex[:8]}",
                action=action,
                description="无需授权的操作",
                agent_id=agent_id,
                target=target,
                status=AuthorizationStatus.APPROVED,
            )
            auto_req.authorized_by = "system_auto"
            return auto_req

        request = AuthorizationRequest(
            request_id=f"auth_{uuid.uuid4().hex[:12]}",
            action=action,
            description=description or CRITICAL_OPERATIONS.get(action, "未知操作"),
            agent_id=agent_id,
            target=target,
        )
        self._pending_requests[request.request_id] = request
        self._publish_auth_request(request)
        logger.warning(
            f"授权请求已创建: {request.request_id} | "
            f"操作: {action} | Agent: {agent_id} | 目标: {target}"
        )
        return request

    def wait_for_authorization(
        self,
        request_id: str,
        timeout: Optional[int] = None,
    ) -> AuthorizationStatus:
        timeout = timeout or self.default_timeout
        request = self._pending_requests.get(request_id)
        if not request:
            logger.error(f"未找到授权请求: {request_id}")
            return AuthorizationStatus.DENIED

        start = time.time()
        while time.time() - start < timeout:
            if request.status == AuthorizationStatus.APPROVED:
                return AuthorizationStatus.APPROVED
            if request.status == AuthorizationStatus.DENIED:
                return AuthorizationStatus.DENIED
            time.sleep(0.5)

        request.status = AuthorizationStatus.TIMEOUT
        request.responded_at = datetime.now(timezone.utc).isoformat()
        logger.warning(f"授权请求超时 ({timeout}s): {request_id} — 默认拒绝")
        return AuthorizationStatus.TIMEOUT

    def approve(self, request_id: str, authorized_by: str) -> bool:
        request = self._pending_requests.get(request_id)
        if not request:
            return False
        request.status = AuthorizationStatus.APPROVED
        request.authorized_by = authorized_by
        request.responded_at = datetime.now(timezone.utc).isoformat()
        self._approved_history.append(request)
        logger.info(f"授权已批准: {request_id} by {authorized_by}")
        return True

    def deny(self, request_id: str, denied_by: str = "user") -> bool:
        request = self._pending_requests.get(request_id)
        if not request:
            return False
        request.status = AuthorizationStatus.DENIED
        request.authorized_by = denied_by
        request.responded_at = datetime.now(timezone.utc).isoformat()
        logger.info(f"授权已拒绝: {request_id} by {denied_by}")
        return True

    def execute_authorized(
        self,
        action: str,
        agent_id: str,
        target: str,
        executor_callback,
        description: str = "",
        approved_by: str = "system",
    ) -> Dict:
        if not self.requires_authorization(action):
            try:
                result = executor_callback()
                return {"status": "executed", "action": action, "result": result}
            except Exception as e:
                return {"status": "error", "action": action, "error": str(e)}

        request = self.create_authorization_request(
            action=action, agent_id=agent_id, target=target, description=description
        )

        if self.approval_callback:
            self.approval_callback(request)

        status = self.wait_for_authorization(request.request_id)

        if status == AuthorizationStatus.APPROVED:
            try:
                result = executor_callback()
                return {
                    "status": "executed",
                    "action": action,
                    "authorization_id": request.request_id,
                    "result": result,
                }
            except Exception as e:
                return {
                    "status": "error",
                    "action": action,
                    "authorization_id": request.request_id,
                    "error": str(e),
                }
        else:
            return {
                "status": "denied",
                "action": action,
                "reason": status.value,
                "authorization_id": request.request_id,
            }

    def _publish_auth_request(self, request: AuthorizationRequest):
        if self.event_bus:
            try:
                from .event_bus import AgentMessage
            except (ImportError, SystemError):
                from event_bus import AgentMessage

            try:
                import asyncio

                message = AgentMessage(
                    sender_id="auth_gateway",
                    receiver_id="user",
                    priority=5,
                    payload={
                        "type": "authorization_request",
                        "request_id": request.request_id,
                        "action": request.action,
                        "description": request.description,
                        "agent_id": request.agent_id,
                        "target": request.target,
                        "timestamp": request.created_at,
                    },
                )

                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self.event_bus.publish(message))
                except RuntimeError:
                    asyncio.run(self.event_bus.publish(message))
            except Exception as e:
                logger.error(f"Error publishing auth request: {e}")

    def get_pending_requests(self) -> List[AuthorizationRequest]:
        return [
            r for r in self._pending_requests.values()
            if r.status == AuthorizationStatus.PENDING
        ]

    def get_authorization_stats(self) -> Dict:
        total = len(self._approved_history) + len(self._pending_requests)
        approved = sum(
            1 for r in self._approved_history
            if r.status == AuthorizationStatus.APPROVED
        )
        denied = sum(
            1 for r in self._approved_history
            if r.status == AuthorizationStatus.DENIED
        )
        return {
            "total_requests": total,
            "approved": approved,
            "denied": denied,
            "pending": len(self._pending_requests),
            "critical_operations": len(CRITICAL_OPERATIONS),
        }
