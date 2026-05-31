"""
spider_meta 多智能体调度系统

使用方式：
    from spider_meta.agents import router, get_local_agent, get_cloud_agent

    # 路由决策
    decision = router.route("分析这个项目的代码结构")
    # → {"role": "data_analyst", "tier": "local", "model": "qwen2.5:7b", ...}

    # 执行本地 Agent
    agent = get_local_agent(decision["role"])
    result = await agent.execute("分析这个项目的代码结构")

    # 执行云端 Agent
    agent = get_cloud_agent(decision["role"])
    result = await agent.execute("分析这个项目的代码结构")
"""

from spider_meta.agents.agent_router import (
    router, AgentRouter, AgentRole, AgentTier,
    AGENT_ROLES, AgentMessage, MessageType,
)
from spider_meta.agents.local import LocalAgent, get_local_agent
from spider_meta.agents.cloud import CloudAgent, get_cloud_agent
from spider_meta.agents.agent_manager import agent_manager, AgentManager, SubTask, TaskStatus
from spider_meta.agents.protocol import delta_sync, lite_proxy, DeltaSyncProtocol, LiteCapabilityProxy

__all__ = [
    "router", "AgentRouter", "AgentRole", "AgentTier",
    "AGENT_ROLES", "AgentMessage", "MessageType",
    "LocalAgent", "get_local_agent",
    "CloudAgent", "get_cloud_agent",
    "agent_manager", "AgentManager", "SubTask", "TaskStatus",
    "delta_sync", "lite_proxy", "DeltaSyncProtocol", "LiteCapabilityProxy",
]
