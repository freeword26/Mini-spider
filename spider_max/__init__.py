"""
Spider MAX v3.0.0 — 大蜘蛛 / 全栈项目管理与多Agent协同平台

集成方式: 项目同步/OKR导入
"""

__version__ = "3.0.0"

from spider_max.core.registry import ModuleRegistry, ModuleCategory, ModuleInfo, module_category_map
from spider_max.core.plugin_manager import PluginManager, Plugin, PluginManifest, PluginStatus


def get_registry() -> ModuleRegistry:
    reg = ModuleRegistry()
    reg.discover_all()
    return reg
