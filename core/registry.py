"""Spider Max 核心模块注册表 — 统一管理所有子模块的生命周期"""
import importlib
import logging
import pkgutil
from typing import Dict, List, Optional, Any, Callable
from enum import Enum


class ModuleCategory(str, Enum):
    CORE = "core"
    OKR = "okr"
    PROJECT = "project"
    TASK = "task"
    AGENT = "agent"
    SKILL = "skill"
    WORKFLOW = "workflow"
    DATA = "data"
    DEVOPS = "devops"
    PMO = "pmo"
    KNOWLEDGE = "knowledge"
    MESSAGE = "message"
    MONITORING = "monitoring"
    INTEGRATION = "integration"


module_category_map: Dict[str, ModuleCategory] = {
    "priority_engine": ModuleCategory.OKR,
    "okr_tracker": ModuleCategory.OKR,
    "project_lifecycle": ModuleCategory.PROJECT,
    "collaboration": ModuleCategory.PROJECT,
    "backup_scheduler": ModuleCategory.CORE,
    "task_allocator": ModuleCategory.TASK,
    "dependency_validator": ModuleCategory.TASK,
    "permission_matrix": ModuleCategory.CORE,
    "timeout_monitor": ModuleCategory.TASK,
    "heartbeat_monitor": ModuleCategory.AGENT,
    "workload_analytics": ModuleCategory.AGENT,
    "skill_7d_model": ModuleCategory.SKILL,
    "skill_version_control": ModuleCategory.SKILL,
    "skill_recommender": ModuleCategory.SKILL,
    "reverse_workflow": ModuleCategory.WORKFLOW,
    "dag_orchestrator": ModuleCategory.WORKFLOW,
    "workflow_templates": ModuleCategory.WORKFLOW,
    "data_collector": ModuleCategory.DATA,
    "etl_engine": ModuleCategory.DATA,
    "data_quality": ModuleCategory.DATA,
    "data_migrator": ModuleCategory.DATA,
    "dashboard_aggregator": ModuleCategory.DATA,
    "vector_store": ModuleCategory.DATA,
    "chaos_engine": ModuleCategory.DEVOPS,
    "deploy_pipeline": ModuleCategory.DEVOPS,
    "automa_integration": ModuleCategory.INTEGRATION,
    "webhook_receiver": ModuleCategory.INTEGRATION,
    "health_selfheal": ModuleCategory.MONITORING,
    "rollback_manager": ModuleCategory.DEVOPS,
    "pmo_manager": ModuleCategory.PMO,
    "agile_kanban": ModuleCategory.PMO,
    "etl_test_framework": ModuleCategory.DATA,
    "sprint_planner": ModuleCategory.PMO,
    "defect_tracker": ModuleCategory.PMO,
    "knowledge_index": ModuleCategory.KNOWLEDGE,
    "progress_metrics": ModuleCategory.PMO,
    "portfolio_manager": ModuleCategory.PMO,
    "report_manager": ModuleCategory.PMO,
    "training_data": ModuleCategory.DATA,
    "message_queue": ModuleCategory.MESSAGE,
    "plugin_manager": ModuleCategory.CORE,
    "distributed_tracing": ModuleCategory.MONITORING,
    "event_consumers": ModuleCategory.MESSAGE,
    "service_mesh": ModuleCategory.CORE,
}


class ModuleInfo:
    def __init__(self, name: str, category: ModuleCategory, module_ref=None):
        self.name = name
        self.category = category
        self.module_ref = module_ref
        self.status = "pending"
        self.functions: List[str] = []

    def load(self) -> bool:
        if self.module_ref is not None:
            self.status = "loaded"
            return True
        try:
            self.module_ref = importlib.import_module(
                f"spider_max.services.{self.name}"
            )
            self.functions = [
                n
                for n in dir(self.module_ref)
                if not n.startswith("_")
                and callable(getattr(self.module_ref, n, None))
            ]
            self.status = "loaded"
            return True
        except ImportError:
            self.status = "missing"
            return False

    def get_endpoints(self) -> List[str]:
        return self.functions


class ModuleRegistry:
    def __init__(self):
        self._modules: Dict[str, ModuleInfo] = {}

    def register(self, name: str, category: ModuleCategory, module_ref=None):
        self._modules[name] = ModuleInfo(name, category, module_ref)

    def get(self, name: str) -> Optional[ModuleInfo]:
        return self._modules.get(name)

    def list(self, category: Optional[ModuleCategory] = None) -> List[ModuleInfo]:
        if category:
            return [m for m in self._modules.values() if m.category == category]
        return list(self._modules.values())

    def discover_all(self):
        for name, category in module_category_map.items():
            info = ModuleInfo(name, category)
            info.load()
            self._modules[name] = info

    def load_by_category(self, category: ModuleCategory) -> List[ModuleInfo]:
        results = []
        for m in self._modules.values():
            if m.category == category and m.status != "loaded":
                if m.load():
                    results.append(m)
        return results

    def get_status_summary(self) -> Dict:
        categories = {}
        loaded = 0
        missing = 0
        for m in self._modules.values():
            cat = m.category.value
            if cat not in categories:
                categories[cat] = {"total": 0, "loaded": 0}
            categories[cat]["total"] += 1
            if m.status == "loaded":
                categories[cat]["loaded"] += 1
                loaded += 1
            else:
                missing += 1
        return {
            "total": len(self._modules),
            "loaded": loaded,
            "missing": missing,
            "by_category": categories,
        }
