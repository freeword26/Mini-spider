#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ConfigRollback — 配置快照与秒级回滚
- 配置变更时自动保存快照（JSON格式）
- 支持 10 秒内回滚到任意历史版本
- 最大保留 20 个快照（FIFO）
"""

import os
import json
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_SNAPSHOT_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "config_snapshots"
DEFAULT_SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
MAX_SNAPSHOTS = 20


class ConfigRollback:
    """配置快照与回滚管理器"""

    def __init__(self, snapshot_dir: Optional[Path] = None, max_snapshots: int = MAX_SNAPSHOTS):
        self.snapshot_dir = snapshot_dir or DEFAULT_SNAPSHOT_DIR
        self.max_snapshots = max_snapshots
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

    def snapshot(self, config_data: Dict, tag: str = "") -> Dict:
        """
        保存当前配置快照。
        返回: {"status": "ok", "snapshot_path": "...", "version": "...", "timestamp": "..."}
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        tag_part = f"_{tag}" if tag else ""
        snapshot_name = f"config_{timestamp}{tag_part}.json"
        snapshot_path = self.snapshot_dir / snapshot_name

        try:
            data = {
                "timestamp": datetime.now().isoformat(),
                "tag": tag,
                "config": config_data,
            }
            snapshot_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            self._cleanup_old()
            logger.info(f"Config snapshot saved: {snapshot_path}")
            return {"status": "ok", "snapshot_path": str(snapshot_path), "tag": tag, "timestamp": data["timestamp"]}
        except Exception as e:
            logger.error(f"Snapshot failed: {e}")
            return {"status": "error", "error": str(e)}

    def rollback(self, steps: int = 1, snapshot_path: Optional[Path] = None) -> Dict:
        """
        回滚配置。
        steps=1 回滚到最近一个快照，steps=2 回滚到倒数第二个，依此类推。
        也可直接指定 snapshot_path 回滚到特定版本。
        目标：10秒内完成。
        """
        try:
            if snapshot_path:
                target = snapshot_path
            else:
                snapshots = self.list_snapshots()
                if not snapshots:
                    return {"status": "error", "error": "No snapshot available for rollback"}
                if steps > len(snapshots):
                    return {"status": "error", "error": f"Only {len(snapshots)} snapshots available, requested {steps}"}
                target = Path(snapshots[steps - 1]["snapshot_path"])

            if not target.exists():
                return {"status": "error", "error": f"Snapshot not found: {target}"}

            data = json.loads(target.read_text(encoding="utf-8"))
            config = data.get("config", {})

            target.with_suffix(".rolling_back").write_text(
                json.dumps(data, ensure_ascii=False), encoding="utf-8"
            )

            logger.info(f"Rolled back to: {target} (tag: {data.get('tag', 'none')})")
            return {
                "status": "ok",
                "rolled_back_to": str(target),
                "tag": data.get("tag", ""),
                "original_timestamp": data.get("timestamp", ""),
                "config": config,
            }

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return {"status": "error", "error": str(e)}

    def list_snapshots(self) -> List[Dict]:
        """列出所有快照（最新在前）"""
        snapshots = []
        for f in sorted(self.snapshot_dir.glob("config_*.json"), reverse=True):
            if f.suffix != ".json":
                continue
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                snapshots.append({
                    "snapshot_path": str(f),
                    "timestamp": data.get("timestamp", ""),
                    "tag": data.get("tag", ""),
                    "size_bytes": f.stat().st_size,
                })
            except Exception:
                snapshots.append({"snapshot_path": str(f), "timestamp": "", "tag": "", "size_bytes": f.stat().st_size})
        return snapshots

    def diff(self, snapshot_a: Path, snapshot_b: Path) -> Dict:
        """比较两个快照的差异"""
        try:
            a = json.loads(Path(snapshot_a).read_text(encoding="utf-8")).get("config", {})
            b = json.loads(Path(snapshot_b).read_text(encoding="utf-8")).get("config", {})
            keys = set(list(a.keys()) + list(b.keys()))
            differences = {}
            for k in keys:
                if a.get(k) != b.get(k):
                    differences[k] = {"before": a.get(k), "after": b.get(k)}
            return {"status": "ok", "differences": differences, "diff_count": len(differences)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _cleanup_old(self):
        """删除超出保留数量限制的旧快照"""
        snapshots = sorted(self.snapshot_dir.glob("config_*.json"), key=lambda f: f.stat().st_mtime)
        while len(snapshots) > self.max_snapshots:
            old = snapshots.pop(0)
            old.unlink(missing_ok=True)
            logger.info(f"Cleaned old snapshot: {old.name}")
