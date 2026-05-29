"""
Agents模块 - 无人值守系统
"""

try:
    from .registry import (
        AgentStatus,
        AgentDefinition,
        AgentRegistry,
        agent_registry
    )
except (ImportError, SystemError):
    from registry import (
        AgentStatus,
        AgentDefinition,
        AgentRegistry,
        agent_registry
    )

__all__ = [
    "AgentStatus",
    "AgentDefinition",
    "AgentRegistry",
    "agent_registry"
]
