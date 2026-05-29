-- Spider Max v3.0.0 — 核心数据库Schema
-- 基于TAPD v3 schema扩展

CREATE TABLE IF NOT EXISTS agents (
    agent_id TEXT PRIMARY KEY,
    role TEXT NOT NULL,
    name TEXT NOT NULL,
    skills TEXT, skill_matrix TEXT,
    max_tasks INTEGER DEFAULT 5,
    current_tasks INTEGER DEFAULT 0,
    availability_score INTEGER DEFAULT 100,
    status TEXT DEFAULT 'active',
    last_active TEXT,
    created_date TEXT DEFAULT (datetime('now')),
    load_threshold REAL DEFAULT 0.8,
    capability_tags TEXT,
    avg_completion_rate REAL DEFAULT 0.0,
    quality_score REAL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS okrs (
    okr_id TEXT PRIMARY KEY,
    okr_name TEXT NOT NULL,
    objective TEXT,
    key_results TEXT,
    status TEXT DEFAULT 'Active',
    confidence_index INTEGER DEFAULT 50,
    achieved_metrics TEXT,
    final_score REAL,
    created_date TEXT DEFAULT (datetime('now')),
    target_date TEXT, archived_date TEXT
);

CREATE TABLE IF NOT EXISTS projects (
    project_id TEXT PRIMARY KEY,
    project_name TEXT NOT NULL,
    project_path TEXT NOT NULL DEFAULT '',
    project_type TEXT, status TEXT DEFAULT '新建',
    priority TEXT DEFAULT 'P2', owner TEXT,
    linked_okr_id TEXT,
    created_date TEXT DEFAULT (datetime('now')),
    deadline TEXT,
    total_tasks INTEGER DEFAULT 0,
    completed_tasks INTEGER DEFAULT 0,
    in_progress_tasks INTEGER DEFAULT 0,
    blocked_tasks INTEGER DEFAULT 0,
    progress_percent INTEGER DEFAULT 0,
    health_status TEXT DEFAULT 'unknown',
    business_value_score INTEGER DEFAULT 0,
    customer_impact TEXT DEFAULT 'medium',
    risk_factors TEXT,
    description TEXT, sop_template TEXT DEFAULT 'standard_sop',
    confidence_index INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    task_name TEXT NOT NULL,
    description TEXT,
    task_type TEXT DEFAULT 'feature',
    acceptance_criteria TEXT,
    status TEXT DEFAULT 'Backlog',
    priority TEXT DEFAULT 'P2',
    complexity_score INTEGER DEFAULT 50,
    assignee TEXT, required_role TEXT,
    created_date TEXT DEFAULT (datetime('now')),
    started_date TEXT, deadline TEXT, completed_date TEXT,
    estimate_hours INTEGER DEFAULT 0,
    actual_hours INTEGER DEFAULT 0,
    progress_percent INTEGER DEFAULT 0,
    risk_level TEXT DEFAULT 'LOW',
    block_reason TEXT, parent_task_id TEXT,
    dependencies TEXT, data_version TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(project_id)
);

CREATE TABLE IF NOT EXISTS skills (
    skill_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT, category TEXT DEFAULT '',
    version TEXT DEFAULT '1.0.0',
    tags TEXT DEFAULT '[]',
    dependencies TEXT DEFAULT '[]',
    parameters TEXT DEFAULT '{}',
    status TEXT DEFAULT 'active',
    created_date TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS workflows (
    workflow_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    definition TEXT DEFAULT '[]',
    trigger_type TEXT DEFAULT 'manual',
    project_id TEXT DEFAULT '',
    status TEXT DEFAULT 'active',
    created_date TEXT DEFAULT (datetime('now'))
);
