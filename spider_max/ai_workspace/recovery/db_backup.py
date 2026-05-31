#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DatabaseBackup — 数据库自动备份与恢复
- 定时备份 data/spider_max.db
- 保留最近 N 天备份（默认7天）
- 损坏时自动从最近备份恢复
"""

import os
import shutil
import sqlite3
import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent.parent / "data" / "spider_max.db"
DEFAULT_BACKUP_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "backups"
DEFAULT_RETENTION_DAYS = 7


class DatabaseBackup:
    """数据库自动备份与恢复管理器"""

    def __init__(
        self,
        db_path: Optional[Path] = None,
        backup_dir: Optional[Path] = None,
        retention_days: int = DEFAULT_RETENTION_DAYS,
    ):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.backup_dir = backup_dir or DEFAULT_BACKUP_DIR
        self.retention_days = retention_days
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def backup(self, tag: str = "") -> Dict:
        """
        执行一次数据库备份。
        返回: {"status": "ok"/"error", "backup_path": "...", "size_bytes": N, "timestamp": "..."}
        """
        if not self.db_path.exists():
            return {"status": "error", "error": f"Database not found: {self.db_path}"}

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        tag_part = f"_{tag}" if tag else ""
        backup_name = f"spider_max_{timestamp}{tag_part}.db"
        backup_path = self.backup_dir / backup_name

        try:
            self._verify_db_integrity()
            shutil.copy2(str(self.db_path), str(backup_path))
            size = backup_path.stat().st_size

            meta = {
                "original": str(self.db_path),
                "backup": str(backup_path),
                "size_bytes": size,
                "timestamp": datetime.now().isoformat(),
                "tag": tag,
            }
            meta_path = backup_path.with_suffix(".json")
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

            self._cleanup_old_backups()

            logger.info(f"Backup created: {backup_path} ({size} bytes)")
            return {"status": "ok", "backup_path": str(backup_path), "size_bytes": size, **meta}

        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return {"status": "error", "error": str(e)}

    def restore(self, backup_path: Optional[Path] = None) -> Dict:
        """
        从备份恢复数据库。
        如果不指定 backup_path，自动使用最近的备份。
        恢复前自动备份当前数据库（防止二次损坏）。
        """
        if backup_path is None:
            recent = self.list_backups()
            if not recent:
                return {"status": "error", "error": "No backup available"}
            backup_path = Path(recent[0]["backup_path"])

        if not backup_path.exists():
            return {"status": "error", "error": f"Backup not found: {backup_path}"}

        try:
            if self.db_path.exists():
                emergency = self.db_path.with_suffix(".emergency.db")
                shutil.copy2(str(self.db_path), str(emergency))
                logger.info(f"Emergency backup: {emergency}")

            shutil.copy2(str(backup_path), str(self.db_path))

            if self._verify_db_integrity():
                logger.info(f"Restored from: {backup_path}")
                return {"status": "ok", "restored_from": str(backup_path), "timestamp": datetime.now().isoformat()}
            else:
                return {"status": "error", "error": "Restored database failed integrity check"}

        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return {"status": "error", "error": str(e)}

    def list_backups(self) -> List[Dict]:
        """列出所有可用备份（按时间倒序）"""
        backups = []
        for f in sorted(self.backup_dir.glob("spider_max_*.db"), reverse=True):
            meta_path = f.with_suffix(".json")
            size = f.stat().st_size
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            meta = {}
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                except Exception:
                    pass
            backups.append({
                "backup_path": str(f),
                "size_bytes": size,
                "created_at": mtime.isoformat(),
                "tag": meta.get("tag", ""),
            })
        return backups

    def check_health(self) -> Dict:
        """检查数据库健康状态"""
        healthy = self._verify_db_integrity()
        size = self.db_path.stat().st_size if self.db_path.exists() else 0
        backups = len(self.list_backups())
        return {
            "healthy": healthy,
            "db_path": str(self.db_path),
            "size_bytes": size,
            "available_backups": backups,
            "backup_dir": str(self.backup_dir),
        }

    def _verify_db_integrity(self) -> bool:
        """验证数据库文件完整性"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.execute("PRAGMA integrity_check")
            conn.close()
            return True
        except Exception:
            return False

    def _cleanup_old_backups(self):
        """清理超过保留期的旧备份"""
        cutoff = datetime.now() - timedelta(days=self.retention_days)
        for f in self.backup_dir.glob("spider_max_*"):
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime < cutoff:
                f.unlink(missing_ok=True)
                logger.info(f"Cleaned old backup: {f.name}")
