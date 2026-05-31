"""
Spider MAX v3.1.0 — 大蜘蛛 / 全栈项目管理与多Agent协同平台
"""

__version__ = "3.1.0"

import importlib
import importlib.util
import sys
from pathlib import Path

_pkg_dir = Path(__file__).resolve().parent


class _AIRootFinder:
    """Meta-path finder for spider_max.ai_workspace submodules."""

    _pkg_dir = _pkg_dir / "ai_workspace"

    @classmethod
    def find_spec(cls, fullname, path=None, target=None):
        if not fullname.startswith("spider_max.ai_workspace."):
            return None
        parts = fullname.split(".")
        rel_parts = parts[2:]
        candidate = cls._pkg_dir
        for part in rel_parts[:-1]:
            candidate = candidate / part
            if not (candidate / "__init__.py").exists():
                return None
        last = rel_parts[-1]
        mod_file = candidate / f"{last}.py"
        if mod_file.exists():
            return importlib.util.spec_from_file_location(fullname, str(mod_file))
        pkg_dir = candidate / last
        init = pkg_dir / "__init__.py"
        if init.exists():
            return importlib.util.spec_from_file_location(
                fullname, str(init), submodule_search_locations=[str(pkg_dir)],
            )
        return None


if not any(type(f) is _AIRootFinder for f in sys.meta_path):
    sys.meta_path.insert(0, _AIRootFinder)

_ai_ws_dir = _pkg_dir / "ai_workspace"
if _ai_ws_dir.is_dir() and (_ai_ws_dir / "__init__.py").exists():
    _fullname = "spider_max.ai_workspace"
    if _fullname not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            _fullname, str(_ai_ws_dir / "__init__.py"),
            submodule_search_locations=[str(_ai_ws_dir)],
        )
        mod = importlib.util.module_from_spec(spec)
        mod.__path__ = [str(_ai_ws_dir)]
        mod.__package__ = _fullname
        sys.modules[_fullname] = mod
        try:
            importlib.import_module(_fullname)
        except Exception:
            pass
    if "spider_max" in sys.modules:
        setattr(sys.modules["spider_max"], "ai_workspace", sys.modules[_fullname])

from spider_max.core.registry import ModuleRegistry, ModuleCategory, ModuleInfo, module_category_map
from spider_max.core.plugin_manager import PluginManager, Plugin, PluginManifest, PluginStatus


def get_registry() -> ModuleRegistry:
    reg = ModuleRegistry()
    reg.discover_all()
    return reg
