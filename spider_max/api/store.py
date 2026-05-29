#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SQLite-backed persistent store for API routers."""

import sqlite3
import json
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from contextlib import contextmanager


class PersistentStore:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_db()

    def _get_conn(self):
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(str(self.db_path))
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
        return self._local.conn

    @contextmanager
    def _cursor(self):
        conn = self._get_conn()
        try:
            yield conn.cursor()
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def _init_db(self):
        with self._cursor() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS workflows (
                    workflow_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    version TEXT DEFAULT '1.0.0',
                    enabled INTEGER DEFAULT 1,
                    tasks TEXT DEFAULT '[]',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS executions (
                    execution_id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    start_time TEXT,
                    end_time TEXT,
                    duration_seconds REAL DEFAULT 0.0,
                    context TEXT DEFAULT '{}',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS schedules (
                    workflow_id TEXT PRIMARY KEY,
                    name TEXT DEFAULT '',
                    trigger_type TEXT DEFAULT 'cron',
                    cron_expression TEXT,
                    interval_seconds INTEGER,
                    enabled INTEGER DEFAULT 1,
                    timezone TEXT DEFAULT 'Asia/Shanghai',
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS agents (
                    agent_id TEXT PRIMARY KEY,
                    agent_name TEXT DEFAULT '',
                    status TEXT DEFAULT 'active',
                    schedule_type TEXT DEFAULT 'daily',
                    time_slots TEXT DEFAULT '[]',
                    assigned_workflows TEXT DEFAULT '[]',
                    current_shift TEXT,
                    last_heartbeat TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def close(self):
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None

    # Workflows
    def list_workflows(self) -> List[Dict]:
        with self._cursor() as c:
            c.execute("SELECT * FROM workflows ORDER BY workflow_id")
            return [dict(r) for r in c.fetchall()]

    def get_workflow(self, workflow_id: str) -> Optional[Dict]:
        with self._cursor() as c:
            c.execute("SELECT * FROM workflows WHERE workflow_id = ?", (workflow_id,))
            r = c.fetchone()
            return dict(r) if r else None

    def create_workflow(self, wf: Dict) -> bool:
        with self._cursor() as c:
            c.execute("""
                INSERT OR REPLACE INTO workflows
                (workflow_id, name, description, version, enabled, tasks, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                wf["workflow_id"], wf.get("name", ""), wf.get("description", ""),
                wf.get("version", "1.0.0"), int(wf.get("enabled", True)),
                json.dumps(wf.get("tasks", []), ensure_ascii=False),
                datetime.now().isoformat()
            ))
        return True

    def update_workflow(self, workflow_id: str, updates: Dict) -> bool:
        wf = self.get_workflow(workflow_id)
        if not wf:
            return False
        wf.update(updates)
        return self.create_workflow(wf)

    def delete_workflow(self, workflow_id: str) -> bool:
        with self._cursor() as c:
            c.execute("DELETE FROM workflows WHERE workflow_id = ?", (workflow_id,))
            return c.rowcount > 0

    # Executions
    def list_executions(self, workflow_id: str = None, limit: int = 100) -> List[Dict]:
        with self._cursor() as c:
            if workflow_id:
                c.execute("SELECT * FROM executions WHERE workflow_id = ? ORDER BY created_at DESC LIMIT ?",
                          (workflow_id, limit))
            else:
                c.execute("SELECT * FROM executions ORDER BY created_at DESC LIMIT ?", (limit,))
            return [dict(r) for r in c.fetchall()]

    def get_execution(self, execution_id: str) -> Optional[Dict]:
        with self._cursor() as c:
            c.execute("SELECT * FROM executions WHERE execution_id = ?", (execution_id,))
            r = c.fetchone()
            return dict(r) if r else None

    def create_execution(self, execution: Dict) -> bool:
        with self._cursor() as c:
            c.execute("""
                INSERT OR REPLACE INTO executions
                (execution_id, workflow_id, status, start_time, end_time, duration_seconds, context)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                execution["execution_id"], execution.get("workflow_id", ""),
                execution.get("status", "pending"),
                execution.get("start_time"), execution.get("end_time"),
                execution.get("duration_seconds", 0.0),
                json.dumps(execution.get("context", {}), ensure_ascii=False)
            ))
        return True

    def update_execution(self, execution_id: str, updates: Dict) -> bool:
        execution = self.get_execution(execution_id)
        if not execution:
            return False
        execution.update(updates)
        return self.create_execution(execution)

    # Schedules
    def list_schedules(self) -> List[Dict]:
        with self._cursor() as c:
            c.execute("SELECT * FROM schedules ORDER BY workflow_id")
            return [dict(r) for r in c.fetchall()]

    def get_schedule(self, workflow_id: str) -> Optional[Dict]:
        with self._cursor() as c:
            c.execute("SELECT * FROM schedules WHERE workflow_id = ?", (workflow_id,))
            r = c.fetchone()
            return dict(r) if r else None

    def create_schedule(self, schedule: Dict) -> bool:
        with self._cursor() as c:
            c.execute("""
                INSERT OR REPLACE INTO schedules
                (workflow_id, name, trigger_type, cron_expression, interval_seconds, enabled, timezone, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                schedule["workflow_id"], schedule.get("name", ""),
                schedule.get("trigger_type", "cron"),
                schedule.get("cron_expression"), schedule.get("interval_seconds"),
                int(schedule.get("enabled", True)), schedule.get("timezone", "Asia/Shanghai"),
                datetime.now().isoformat()
            ))
        return True

    def update_schedule(self, workflow_id: str, updates: Dict) -> bool:
        schedule = self.get_schedule(workflow_id)
        if not schedule:
            return False
        schedule.update(updates)
        return self.create_schedule(schedule)

    # Agents
    def list_agents(self) -> List[Dict]:
        with self._cursor() as c:
            c.execute("SELECT * FROM agents ORDER BY agent_id")
            return [dict(r) for r in c.fetchall()]

    def get_agent(self, agent_id: str) -> Optional[Dict]:
        with self._cursor() as c:
            c.execute("SELECT * FROM agents WHERE agent_id = ?", (agent_id,))
            r = c.fetchone()
            return dict(r) if r else None

    def create_agent(self, agent: Dict) -> bool:
        with self._cursor() as c:
            c.execute("""
                INSERT OR REPLACE INTO agents
                (agent_id, agent_name, status, schedule_type, time_slots, assigned_workflows,
                 current_shift, last_heartbeat, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                agent["agent_id"], agent.get("agent_name", ""),
                agent.get("status", "active"), agent.get("schedule_type", "daily"),
                json.dumps(agent.get("time_slots", []), ensure_ascii=False),
                json.dumps(agent.get("assigned_workflows", []), ensure_ascii=False),
                agent.get("current_shift"), agent.get("last_heartbeat"),
                datetime.now().isoformat()
            ))
        return True

    def update_agent(self, agent_id: str, updates: Dict) -> bool:
        agent = self.get_agent(agent_id)
        if not agent:
            return False
        agent.update(updates)
        return self.create_agent(agent)
