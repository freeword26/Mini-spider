#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件安全访问层 — 三层闭环架构冲突#1解决方案
所有文件操作通过此层进行，包含白名单路径检查和审计日志
"""

import os
import logging
from pathlib import Path
from typing import List, Optional, Set
from datetime import datetime, timezone
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class FileAccessRecord:
    timestamp: str
    action: str
    path: str
    allowed: bool
    agent_id: str = "unknown"
    reason: str = ""


DEFAULT_WHITELIST = {
    "e:\\软件开发\\.ai-workspace",
    "e:\\软件开发\\07_临时文件",
    "e:\\软件开发\\3_任务执行中枢（TAPD）\\03_任务看板",
    "e:\\软件开发\\3_任务执行中枢（TAPD）\\07_监控报告",
    "e:\\软件开发\\3_任务执行中枢（TAPD）\\07_数据库",
    "e:\\软件开发\\stats",
    "e:\\软件开发\\archives",
}

DEFAULT_BLACKLIST = {
    "e:\\软件开发\\.env",
    "e:\\软件开发\\.git",
    "e:\\软件开发\\config\\credentials",
    "e:\\软件开发\\config\\secrets",
}


class FileAccessLayer:
    """文件安全访问层 — 封装所有文件操作"""

    def __init__(
        self,
        whitelist: Optional[Set[str]] = None,
        blacklist: Optional[Set[str]] = None,
        raise_on_violation: bool = False,
    ):
        self.whitelist = {os.path.normpath(p) for p in (whitelist or DEFAULT_WHITELIST)}
        self.blacklist = {os.path.normpath(p) for p in (blacklist or DEFAULT_BLACKLIST)}
        self.raise_on_violation = raise_on_violation
        self._audit_log: List[FileAccessRecord] = []
        self._access_count = 0
        self._denied_count = 0

    def _is_allowed(self, path: str) -> bool:
        norm_path = os.path.normpath(path)

        for blocked in self.blacklist:
            if norm_path.startswith(blocked) or blocked in norm_path:
                return False

        for allowed in self.whitelist:
            if norm_path.startswith(allowed):
                return True

        return False

    def _log_access(
        self,
        action: str,
        path: str,
        allowed: bool,
        agent_id: str = "unknown",
        reason: str = "",
    ):
        record = FileAccessRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action=action,
            path=path,
            allowed=allowed,
            agent_id=agent_id,
            reason=reason,
        )
        self._audit_log.append(record)
        self._access_count += 1
        if not allowed:
            self._denied_count += 1
        status = "ALLOWED" if allowed else "DENIED"
        logger.debug(f"FileAccess [{status}] {action}: {path}")

    def _check(
        self, action: str, path: str, agent_id: str = "unknown"
    ) -> bool:
        allowed = self._is_allowed(path)
        self._log_access(action, path, allowed, agent_id)
        if not allowed:
            msg = f"File access denied: {action} on {path} (agent: {agent_id})"
            logger.warning(msg)
            if self.raise_on_violation:
                raise PermissionError(msg)
        return allowed

    def read(self, path: str, agent_id: str = "unknown") -> Optional[str]:
        if not self._check("read", path, agent_id):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"File read error: {path}: {e}")
            return None

    def read_bytes(self, path: str, agent_id: str = "unknown") -> Optional[bytes]:
        if not self._check("read", path, agent_id):
            return None
        try:
            with open(path, "rb") as f:
                return f.read()
        except Exception as e:
            logger.error(f"File read error: {path}: {e}")
            return None

    def write(
        self, path: str, content: str, agent_id: str = "unknown", encoding: str = "utf-8"
    ) -> bool:
        if not self._check("write", path, agent_id):
            return False
        try:
            parent = Path(path).parent
            parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding=encoding) as f:
                f.write(content)
            return True
        except Exception as e:
            logger.error(f"File write error: {path}: {e}")
            return False

    def write_bytes(self, path: str, content: bytes, agent_id: str = "unknown") -> bool:
        if not self._check("write", path, agent_id):
            return False
        try:
            parent = Path(path).parent
            parent.mkdir(parents=True, exist_ok=True)
            with open(path, "wb") as f:
                f.write(content)
            return True
        except Exception as e:
            logger.error(f"File write error: {path}: {e}")
            return False

    def delete(self, path: str, agent_id: str = "unknown") -> bool:
        if not self._check("delete", path, agent_id):
            return False
        try:
            os.remove(path)
            return True
        except Exception as e:
            logger.error(f"File delete error: {path}: {e}")
            return False

    def exists(self, path: str, agent_id: str = "unknown") -> bool:
        self._check("exists", path, agent_id)
        return os.path.exists(path)

    def ensure_dir(self, path: str, agent_id: str = "unknown") -> bool:
        norm_path = os.path.normpath(path)
        for allowed in self.whitelist:
            if norm_path.startswith(allowed):
                try:
                    os.makedirs(path, exist_ok=True)
                    return True
                except Exception as e:
                    logger.error(f"Dir create error: {path}: {e}")
                    return False
        logger.warning(f"Dir create denied: {path}")
        return False

    def get_audit_log(self, limit: int = 100) -> List[FileAccessRecord]:
        return self._audit_log[-limit:]

    def get_stats(self) -> Dict:
        return {
            "total_access": self._access_count,
            "denied": self._denied_count,
            "allowed": self._access_count - self._denied_count,
            "whitelist_entries": len(self.whitelist),
            "blacklist_entries": len(self.blacklist),
        }
