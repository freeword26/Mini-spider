"""Spider Max — 数据库管理模块"""
from pathlib import Path
from typing import Dict, Optional
import sqlite3


class DatabaseManager:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = str(Path(__file__).resolve().parent.parent / "data" / "spider_max.db")
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path

    def get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def get_stats(self) -> Dict:
        conn = self.get_conn()
        stats = {}
        for t in ['projects', 'tasks', 'agents', 'okrs', 'alerts', 'sync_log', 'skills', 'workflows']:
            try:
                cnt = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                stats[t] = cnt
            except Exception:
                stats[t] = -1
        conn.close()
        return stats

    def execute_sql(self, sql: str, params: tuple = ()):
        conn = self.get_conn()
        cursor = conn.execute(sql, params)
        conn.commit()
        rows = [dict(r) for r in cursor.fetchall()] if cursor.description else []
        conn.close()
        return rows
