#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""工作流定义 — 预定义的工作流实现"""

try:
    from .wf_001_data_sync import DataSyncWorkflow
    from .wf_002_task_tracking import TaskTrackingWorkflow
    from .wf_003_overdue_alert import OverdueAlertWorkflow
    from .wf_004_cicd import CICDWorkflow
    from .wf_005_compliance import ComplianceWorkflow
    from .wf_006_backup import BackupWorkflow
    from .wf_007_git_sync import GitHubSyncWorkflow
    from .wf_008_log_analysis import LogAnalysisWorkflow
    from .wf_011_doc_slice import DocSliceWorkflow
    from .wf_012_ctx_track import ContextTrackWorkflow
    from .wf_013_agent_collect import AgentCollectWorkflow
    from .wf_014_doc_archive import DocArchiveWorkflow
    from .wf_lifecycle_scan import (
        LifecycleDailyScanWorkflow,
        LifecycleWeeklyArchiveWorkflow,
        LifecycleWeeklyDedupWorkflow,
    )
    from .wf_okr_report import OKRReportWorkflow
    from .wf_daily_ops import DailyOpsWorkflow
except (ImportError, SystemError):
    from wf_001_data_sync import DataSyncWorkflow
    from wf_002_task_tracking import TaskTrackingWorkflow
    from wf_003_overdue_alert import OverdueAlertWorkflow
    from wf_004_cicd import CICDWorkflow
    from wf_005_compliance import ComplianceWorkflow
    from wf_006_backup import BackupWorkflow
    from wf_007_git_sync import GitHubSyncWorkflow
    from wf_008_log_analysis import LogAnalysisWorkflow
    from wf_011_doc_slice import DocSliceWorkflow
    from wf_012_ctx_track import ContextTrackWorkflow
    from wf_013_agent_collect import AgentCollectWorkflow
    from wf_014_doc_archive import DocArchiveWorkflow
    from wf_lifecycle_scan import (
        LifecycleDailyScanWorkflow,
        LifecycleWeeklyArchiveWorkflow,
        LifecycleWeeklyDedupWorkflow,
    )
    from wf_okr_report import OKRReportWorkflow
    from wf_daily_ops import DailyOpsWorkflow

__all__ = [
    "DataSyncWorkflow", "TaskTrackingWorkflow", "OverdueAlertWorkflow",
    "CICDWorkflow", "ComplianceWorkflow", "BackupWorkflow",
    "GitHubSyncWorkflow", "LogAnalysisWorkflow",
    "DocSliceWorkflow", "ContextTrackWorkflow", "AgentCollectWorkflow",
    "DocArchiveWorkflow",
    "LifecycleDailyScanWorkflow", "LifecycleWeeklyArchiveWorkflow",
    "LifecycleWeeklyDedupWorkflow",
    "OKRReportWorkflow", "DailyOpsWorkflow",
]
