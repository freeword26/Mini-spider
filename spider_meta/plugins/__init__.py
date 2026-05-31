"""
spider_meta Plugin System

Compatible with the broader Spider ecosystem skills.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class SkillPlugin(ABC):
    """Base class for Spider-compatible skill plugins."""

    name: str = "base_skill"
    version: str = "0.1.0"
    description: str = "Base skill plugin"

    @abstractmethod
    def activate(self, context: Dict[str, Any]) -> None:
        """Activate the skill with given context."""
        ...

    @abstractmethod
    async def execute(self, task: Any) -> Any:
        """Execute the skill on a given task."""
        ...

    def validate(self, params: Dict[str, Any]) -> bool:
        """Validate input parameters."""
        return True

    def deactivate(self) -> None:
        """Deactivate the skill."""
        pass


class PluginRegistry:
    """Global plugin registry for spider_meta skills.

    When `_tool_registry` is set, registered plugins automatically
    appear as tools in the Meta-Agent ToolRegistry.
    """

    _plugins: Dict[str, SkillPlugin] = {}
    _tool_registry = None

    @classmethod
    def set_tool_registry(cls, tool_registry) -> None:
        """Bind a ToolRegistry so plugins auto-register as tools."""
        cls._tool_registry = tool_registry

    @classmethod
    def register(cls, plugin: SkillPlugin) -> None:
        cls._plugins[plugin.name] = plugin
        if cls._tool_registry is not None:
            cls._tool_registry.register(
                name=plugin.name,
                func=plugin.execute,
                description=plugin.description,
            )

    @classmethod
    def get(cls, name: str) -> Optional[SkillPlugin]:
        return cls._plugins.get(name)

    @classmethod
    def list_plugins(cls) -> Dict[str, str]:
        return {name: p.version for name, p in cls._plugins.items()}


def register_skill(cls):
    """Decorator to register a skill plugin (auto-syncs as a tool)."""
    PluginRegistry.register(cls())
    return cls


__all__ = ["SkillPlugin", "PluginRegistry", "register_skill"]
