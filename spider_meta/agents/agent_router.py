"""
spider_meta Agent Router — 任务调度中枢

架构：
    ┌─────────────────────────────────────────────────┐
    │              AgentRouter (任务调度中枢)            │
    │  角色定义 & 任务分配 & 消息路由 & 成本优化         │
    └──────────────┬──────────────────┬───────────────┘
                   │                  │
    ┌──────────────▼──────┐  ┌────────▼──────────────┐
    │   本地AI智能体        │  │   云端AI智能体          │
    │  - 代码工程师         │  │  - 情报收集员           │
    │  - 文档处理员         │  │  - 社交媒体写手         │
    │  - 数据分析师         │  │  - 创意策划师           │
    └──────────┬───────────┘  └────────┬──────────────┘
               │                       │
    ┌──────────▼───────────┐  ┌────────▼──────────────┐
    │  本地Docker容器        │  │  云端API服务            │
    │  - Ollama (Qwen)      │  │  - Kilo Code API       │
    │  - Llama.cpp          │  │  - DeepSeek             │
    └──────────────────────┘  └───────────────────────┘

硬件约束（立项协议）：
  GPU_MEMORY_LIMIT=3500M  CPU_CORE_LIMIT=3.0
  RAM_LIMIT=16G           DISK_ALERT=85%
  月成本上限：¥50/月
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from spider_meta.cost_guard import budget_mgr
from spider_meta.config import HARDWARE_LIMITS

logger = logging.getLogger("spider_meta.router")


# ============================================================
# 消息协议
# ============================================================

class MessageType(str, Enum):
    TASK_REQUEST    = "task.request"     # Router → Agent
    TASK_RESPONSE   = "task.response"    # Agent → Router
    TASK_STATUS     = "task.status"      # Agent → Router 进度
    HEARTBEAT       = "heartbeat"        # Agent → Router 存活
    ROUTE           = "route"            # Router 内部路由
    ERROR           = "error"            # 错误上报


@dataclass
class AgentMessage:
    """Agent 间通信消息"""
    msg_type: MessageType
    sender: str
    receiver: str
    payload: Dict[str, Any] = field(default_factory=dict)
    msg_id: str = field(default_factory=lambda: f"msg-{uuid.uuid4().hex[:8]}")
    ts: str = field(default_factory=lambda: datetime.now().isoformat())
    correlation_id: str = ""  # 关联同一任务的多条消息


# ============================================================
# Agent 角色定义
# ============================================================

class AgentTier(str, Enum):
    LOCAL  = "local"   # 本地推理（零成本）
    CLOUD  = "cloud"   # 云端API（付费）


@dataclass
class AgentRole:
    """Agent 角色定义"""
    name: str
    tier: AgentTier
    model: str
    system_prompt: str
    skills: List[str]
    max_tokens: int = 4096
    temperature: float = 0.1
    cost_per_million: float = 0.0   # ¥/百万 tokens
    fallback_role: str = ""         # 降级时切换的角色


# ---- 6个Agent角色 ----

AGENT_ROLES: Dict[str, AgentRole] = {
    # === 本地AI智能体（零/低成本）===
    "code_engineer": AgentRole(
        name="code_engineer",
        tier=AgentTier.LOCAL,
        model="qwen2.5-coder:7b",
        system_prompt="你是代码工程师。专精：Python/Shell/代码调试/文件操作。"
                      "使用 shell、read_file、write_file、search_files 工具完成任务。"
                      "响应JSON格式：{\"thought\":\"\",\"action\":\"\",\"action_input\":{}}",
        skills=["coding", "debugging", "shell", "git", "refactor"],
        cost_per_million=0.0,   # 本地 Ollama 零成本
        fallback_role="cloud_coder",
    ),
    "doc_processor": AgentRole(
        name="doc_processor",
        tier=AgentTier.LOCAL,
        model="qwen2.5:7b",
        system_prompt="你是文档处理员。专精：文档解析/格式化/翻译/摘要/报告生成。"
                      "使用 read_file、write_file、search_files 工具处理文档。",
        skills=["nlp", "translation", "summarization", "report_gen", "markdown"],
        cost_per_million=0.0,
        fallback_role="cloud_writer",
    ),
    "data_analyst": AgentRole(
        name="data_analyst",
        tier=AgentTier.LOCAL,
        model="qwen2.5:7b",
        system_prompt="你是数据分析师。专精：CSV/JSON/日志分析/统计/图表建议。"
                      "使用 read_file、write_file、shell 处理数据文件。"
                      "本地无法生成图表时明确说明，给出 Python 代码建议。",
        skills=["csv", "json", "statistics", "logging", "visualization_advice"],
        cost_per_million=0.0,
        fallback_role="cloud_analyst",
    ),

    # === 云端AI智能体（付费但能力更强）===
    "intel_collector": AgentRole(
        name="intel_collector",
        tier=AgentTier.CLOUD,
        model="deepseek-chat",
        system_prompt="你是情报收集员。专精：网络搜索/信息聚合/竞品分析/趋势研判。"
                      "使用 http_get、search_files 收集信息。"
                      "输出结构化情报报告。",
        skills=["web_search", "intelligence", "competitive_analysis", "trends"],
        max_tokens=8192,
        cost_per_million=0.14,   # DeepSeek ¥0.14/1M
        fallback_role="doc_processor",
    ),
    "social_writer": AgentRole(
        name="social_writer",
        tier=AgentTier.CLOUD,
        model="deepseek-chat",
        system_prompt="你是社交媒体写手。专精：文案撰写/内容策划/多平台适配/用户互动。"
                      "使用 write_file 输出文案。风格活泼、简洁、有吸引力。",
        skills=["copywriting", "content_plan", "platform_adapt", "engagement"],
        max_tokens=4096,
        cost_per_million=0.14,
        fallback_role="doc_processor",
    ),
    "creative_strategist": AgentRole(
        name="creative_strategist",
        tier=AgentTier.CLOUD,
        model="gpt-4o-mini",
        system_prompt="你是创意策划师。专精：创意构思/方案设计/头脑风暴/策略制定。"
                      "使用 write_file 输出策划方案。思维发散、逻辑清晰。",
        skills=["brainstorm", "strategy", "creative", "planning", "innovation"],
        max_tokens=8192,
        cost_per_million=0.11,
        fallback_role="doc_processor",
    ),
}


# ============================================================
# AgentRouter — 任务调度中枢
# ============================================================

class AgentRouter:
    """
    任务调度中枢：
    1. 根据任务类型和成本预算选择最优 Agent
    2. 本地优先，云端兜底
    3. 单点故障自动降级
    4. 消息路由 & 状态管理
    """

    def __init__(self):
        self.roles = AGENT_ROLES
        self._local_agent = None  # 延迟初始化
        self._message_queue: List[AgentMessage] = []
        self._active_tasks: Dict[str, dict] = {}

    # ---- 核心：路由决策 ----

    def route(self, task: str, preferred_role: str = None,
              force_tier: str = None) -> dict:
        """
        根据任务内容 + 预算 + 硬件资源，路由到最优 Agent。
        
        返回：
          {"role": str, "tier": str, "model": str, "reason": str}
        """
        # 1. 指定角色
        if preferred_role and preferred_role in self.roles:
            role = self.roles[preferred_role]
            return {
                "role": role.name,
                "tier": role.tier.value,
                "model": role.model,
                "reason": f"用户指定角色: {preferred_role}",
            }

        # 2. 硬件检查 — 本地推理是否可行
        hw_ok = self._check_local_capacity()

        # 3. 成本检查 — 今天还有没有预算
        cost_report = budget_mgr.report()
        budget_ok = cost_report["status"] in ("ok", "warning")

        # 4. 任务技能匹配
        role_name = self._match_role_by_skills(task)

        if role_name:
            role = self.roles[role_name]
            # 云端角色但预算不足 → 降级到本地
            if role.tier == AgentTier.CLOUD and not budget_ok:
                fallback = self.roles.get(role.fallback_role, self.roles["doc_processor"])
                return {
                    "role": fallback.name,
                    "tier": fallback.tier.value,
                    "model": fallback.model,
                    "reason": f"预算不足（{cost_report['status']}），降级 {role.name} → {fallback.name}",
                }
            # 本地角色但 GPU 不足 → 尝试轻量本地模型
            if role.tier == AgentTier.LOCAL and not hw_ok:
                return {
                    "role": role.name,
                    "tier": "cloud",   # 本地跑不了，上云端
                    "model": "deepseek-chat",  # 便宜的云端
                    "reason": f"本地GPU显存不足 {HARDWARE_LIMITS['gpu_memory_limit_mb']}MB, 切云端兜底",
                }
            return {
                "role": role.name,
                "tier": role.tier.value,
                "model": role.model,
                "reason": "技能匹配最优角色",
            }

        # 5. 默认：用本地 doc_processor
        return {
            "role": "doc_processor",
            "tier": "local",
            "model": "qwen2.5:7b",
            "reason": "无匹配角色，默认本地文档处理",
        }

    def _match_role_by_skills(self, task: str) -> Optional[str]:
        """根据任务关键词匹配最优角色"""
        task_lower = task.lower()

        # 本地 Agent 关键词
        code_kw     = ["代码", "编程", "python", "shell", "脚本", "debug", "修复", "代码工程", "coding", "script"]
        doc_kw      = ["文档", "报告", "摘要", "翻译", "markdown", "总结", "文档处理", "report", "summary"]
        data_kw     = ["数据", "分析", "csv", "json", "日志", "统计", "chart", "data", "analysis"]

        # 云端 Agent 关键词
        intel_kw    = ["情报", "搜索", "竞品", "趋势", "行情", "调研", "intelligence", "search"]
        social_kw   = ["文案", "社交媒体", "微博", "公众号", "内容", "营销", "social", "copywriting"]
        creative_kw = ["创意", "策划", "方案", "策略", "头脑风暴", "creative", "strategy", "brainstorm"]

        # 按优先级匹配（本地优先）
        if any(k in task_lower for k in code_kw):     return "code_engineer"
        if any(k in task_lower for k in doc_kw):      return "doc_processor"
        if any(k in task_lower for k in data_kw):     return "data_analyst"
        if any(k in task_lower for k in intel_kw):    return "intel_collector"
        if any(k in task_lower for k in social_kw):   return "social_writer"
        if any(k in task_lower for k in creative_kw): return "creative_strategist"

        return None

    @staticmethod
    def _check_local_capacity() -> bool:
        """检查本地是否有足够的 GPU 显存运行推理"""
        try:
            import subprocess
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.free",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5,
            )
            if result.stdout.strip():
                free_mb = int(result.stdout.strip().split("\n")[0])
                # 7B 模型约需 4.5GB，留 1GB buffer
                return free_mb > HARDWARE_LIMITS["gpu_memory_limit_mb"]
        except Exception:
            pass
        return False

    # ---- 消息路由 ----

    def create_message(self, msg_type: MessageType, sender: str,
                       receiver: str, payload: dict) -> AgentMessage:
        msg = AgentMessage(
            msg_type=msg_type, sender=sender,
            receiver=receiver, payload=payload,
        )
        self._message_queue.append(msg)
        return msg

    def get_messages(self, receiver: str = None,
                     msg_type: MessageType = None) -> List[AgentMessage]:
        msgs = self._message_queue
        if receiver:
            msgs = [m for m in msgs if m.receiver == receiver]
        if msg_type:
            msgs = [m for m in msgs if m.msg_type == msg_type]
        return msgs

    # ---- 任务管理 ----

    def register_task(self, task: str, role: str) -> str:
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        self._active_tasks[task_id] = {
            "task": task, "role": role,
            "status": "pending", "created_at": datetime.now().isoformat(),
        }
        return task_id

    def get_task(self, task_id: str) -> Optional[dict]:
        return self._active_tasks.get(task_id)

    # ---- 报告 ----

    def report(self) -> dict:
        cost = budget_mgr.report()
        return {
            "roles": {name: {
                "tier": r.tier.value,
                "model": r.model,
                "skills": r.skills,
                "cost_per_million": r.cost_per_million,
            } for name, r in self.roles.items()},
            "active_tasks": len(self._active_tasks),
            "pending_messages": len(self._message_queue),
            "cost_status": cost["status"],
            "daily_pct": cost["daily"]["pct"],
            "monthly_pct": cost["monthly"]["pct"],
        }


# 全局单例
router = AgentRouter()
