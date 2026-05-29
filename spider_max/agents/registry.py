"""
Agent注册表 - 无人值守系统 (完整版 v2.0)
22个Agent覆盖三层闭环架构所有角色
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class AgentStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ON_LEAVE = "on_leave"
    BUSY = "busy"


@dataclass
class AgentDefinition:
    agent_id: str
    name: str
    role: str
    permission_level: str
    description: str
    layer: str = ""
    status: AgentStatus = AgentStatus.ACTIVE
    assigned_workflows: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


class AgentRegistry:
    def __init__(self):
        self._agents: Dict[str, AgentDefinition] = {}
        self._initialize_default_agents()

    def _initialize_default_agents(self):
        from datetime import datetime
        now = datetime.now().isoformat()

        # ===== 指挥控制层 (L4-L3) =====
        self.register_agent(AgentDefinition(
            agent_id="system-manager", name="系统经理", role="system-manager",
            permission_level="Level 4", description="系统监控、逾期预警、晨会报告",
            layer="指挥控制层",
            assigned_workflows=["WF-003", "WF-008", "WF-015", "WF-016"],
            skills=["系统监控", "逾期预警", "报告生成", "架构协调"],
            created_at=now, updated_at=now
        ))
        self.register_agent(AgentDefinition(
            agent_id="project-manager", name="项目经理", role="project-manager",
            permission_level="Level 4", description="项目看板管理、进度汇报、OKR跟踪",
            layer="指挥控制层",
            assigned_workflows=["WF-014", "WF-016"],
            skills=["项目管理", "OKR跟踪", "进度汇报"],
            created_at=now, updated_at=now
        ))
        self.register_agent(AgentDefinition(
            agent_id="meta-agent", name="Meta-Agent元智能体", role="meta-agent",
            permission_level="Level 4", description="元认知调度、决策协调",
            layer="指挥控制层",
            assigned_workflows=["WF-013"],
            skills=["元认知", "决策协调", "反思学习"],
            created_at=now, updated_at=now
        ))

        # ===== 执行协作层 (L3-L2) =====
        self.register_agent(AgentDefinition(
            agent_id="tech-expert", name="技术专家", role="tech-expert",
            permission_level="Level 3", description="数据库备份、系统监控、日志清理",
            layer="执行协作层",
            assigned_workflows=["WF-005", "WF-006", "WF-015"],
            skills=["数据库备份", "系统监控", "日志管理", "健康检查"],
            created_at=now, updated_at=now
        ))
        self.register_agent(AgentDefinition(
            agent_id="data-scientist", name="数据科学家", role="data-scientist",
            permission_level="Level 3", description="数据同步、合规检查、数据处理",
            layer="执行协作层",
            assigned_workflows=["WF-001", "WF-005"],
            skills=["数据同步", "合规检查", "数据处理"],
            created_at=now, updated_at=now
        ))
        self.register_agent(AgentDefinition(
            agent_id="learning-hacker", name="学习黑客", role="learning-hacker",
            permission_level="Level 3", description="CI/CD、文档切片、上下文追踪",
            layer="执行协作层",
            assigned_workflows=["WF-004", "WF-009", "WF-010", "WF-011", "WF-012", "WF-014"],
            skills=["CI/CD", "文档切片", "上下文追踪", "自适应学习"],
            created_at=now, updated_at=now
        ))
        self.register_agent(AgentDefinition(
            agent_id="skill-manager", name="技能管家", role="skill-manager",
            permission_level="Level 3", description="技能库维护、知识库更新、术语生成",
            layer="执行协作层",
            assigned_workflows=["WF-001", "WF-002", "WF-003"],
            skills=["技能管理", "数据同步", "术语生成", "知识库维护"],
            created_at=now, updated_at=now
        ))
        self.register_agent(AgentDefinition(
            agent_id="langchain-orchestrator", name="LangChain编排器", role="langchain-orchestrator",
            permission_level="Level 3", description="向量数据库同步、存储维护",
            layer="执行协作层",
            assigned_workflows=["WF-001"],
            skills=["向量数据库", "存储同步", "LangChain"],
            created_at=now, updated_at=now
        ))
        self.register_agent(AgentDefinition(
            agent_id="expert-biz-doctor", name="业务医生", role="expert-biz-doctor",
            permission_level="Level 2", description="合规检查、业务流程审查",
            layer="执行协作层",
            assigned_workflows=["WF-005"],
            skills=["合规检查", "业务审查"],
            created_at=now, updated_at=now
        ))
        self.register_agent(AgentDefinition(
            agent_id="devops", name="DevOps工程师", role="devops",
            permission_level="Level 3", description="CI/CD、部署监控、GitHub同步",
            layer="执行协作层",
            assigned_workflows=["WF-004", "WF-007"],
            skills=["CI/CD", "部署监控", "基础设施", "GitHub管理"],
            created_at=now, updated_at=now
        ))

        # ===== 资源与环境层 (L3-L1) =====
        self.register_agent(AgentDefinition(
            agent_id="humanities-scholar", name="人文学者", role="humanities-scholar",
            permission_level="Level 2", description="知识库索引、人文知识管理",
            layer="资源与环境层",
            assigned_workflows=["WF-003"],
            skills=["知识库索引", "人文知识", "文档分析"],
            created_at=now, updated_at=now
        ))
        self.register_agent(AgentDefinition(
            agent_id="developer", name="开发者", role="developer",
            permission_level="Level 3", description="代码开发、快反开发模式",
            layer="资源与环境层",
            assigned_workflows=["WF-013"],
            skills=["代码开发", "快反模式", "技术实现"],
            created_at=now, updated_at=now
        ))
        self.register_agent(AgentDefinition(
            agent_id="qa", name="测试工程师", role="qa",
            permission_level="Level 2", description="测试验证、质量保障",
            layer="资源与环境层",
            assigned_workflows=["WF-013"],
            skills=["测试验证", "质量保障", "用例设计"],
            created_at=now, updated_at=now
        ))
        self.register_agent(AgentDefinition(
            agent_id="analyst", name="分析师", role="analyst",
            permission_level="Level 2", description="数据分析、场景式销售",
            layer="资源与环境层",
            assigned_workflows=["WF-013"],
            skills=["数据分析", "场景建模", "销售分析"],
            created_at=now, updated_at=now
        ))
        self.register_agent(AgentDefinition(
            agent_id="product-manager", name="产品经理", role="product-manager",
            permission_level="Level 2", description="产品设计、元智能体辅助",
            layer="资源与环境层",
            assigned_workflows=["WF-013"],
            skills=["产品设计", "需求分析", "用户研究"],
            created_at=now, updated_at=now
        ))
        self.register_agent(AgentDefinition(
            agent_id="security-architect", name="安全架构师", role="security-architect",
            permission_level="Level 2", description="安全审查、权限边界管理",
            layer="资源与环境层",
            assigned_workflows=["WF-005"],
            skills=["安全审查", "权限管理", "架构安全"],
            created_at=now, updated_at=now
        ))
        self.register_agent(AgentDefinition(
            agent_id="memory-butler", name="记忆管家", role="memory-butler",
            permission_level="Level 2", description="全局状态管理、记忆库维护",
            layer="资源与环境层",
            assigned_workflows=["WF-010", "WF-012"],
            skills=["状态管理", "记忆维护", "上下文追踪"],
            created_at=now, updated_at=now
        ))
        self.register_agent(AgentDefinition(
            agent_id="master-mentor", name="大师导师", role="master-mentor",
            permission_level="Level 2", description="自适应学习、技能培训",
            layer="资源与环境层",
            assigned_workflows=["WF-004"],
            skills=["自适应学习", "技能培训", "知识传授"],
            created_at=now, updated_at=now
        ))
        self.register_agent(AgentDefinition(
            agent_id="math-professor", name="数学教授", role="math-professor",
            permission_level="Level 1", description="数据分析、统计计算",
            layer="资源与环境层",
            assigned_workflows=["WF-013"],
            skills=["数学分析", "统计算法", "数据建模"],
            created_at=now, updated_at=now
        ))
        self.register_agent(AgentDefinition(
            agent_id="trend-forecast", name="趋势预测师", role="trend-forecast",
            permission_level="Level 1", description="趋势分析、数据可视化",
            layer="资源与环境层",
            assigned_workflows=["WF-013"],
            skills=["趋势分析", "预测建模", "数据可视化"],
            created_at=now, updated_at=now
        ))
        self.register_agent(AgentDefinition(
            agent_id="business", name="业务专家", role="business",
            permission_level="Level 1", description="业务流程、多元化知识",
            layer="资源与环境层",
            assigned_workflows=["WF-005"],
            skills=["业务流程", "行业知识", "多元文化"],
            created_at=now, updated_at=now
        ))
        self.register_agent(AgentDefinition(
            agent_id="wen-shi-expert", name="文史专家", role="wen-shi-expert",
            permission_level="Level 1", description="多元文化知识库、人文研究",
            layer="资源与环境层",
            assigned_workflows=["WF-003"],
            skills=["文化研究", "人文知识", "多元文化"],
            created_at=now, updated_at=now
        ))

    def register_agent(self, agent: AgentDefinition) -> None:
        self._agents[agent.agent_id] = agent

    def get_agent(self, agent_id: str) -> Optional[AgentDefinition]:
        return self._agents.get(agent_id)

    def get_all_agents(self) -> List[AgentDefinition]:
        return list(self._agents.values())

    def get_agents_by_workflow(self, workflow_id: str) -> List[AgentDefinition]:
        return [a for a in self._agents.values() if workflow_id in a.assigned_workflows]

    def get_agents_by_layer(self, layer: str) -> List[AgentDefinition]:
        return [a for a in self._agents.values() if a.layer == layer]

    def update_agent_status(self, agent_id: str, status: AgentStatus) -> None:
        if agent_id in self._agents:
            from datetime import datetime
            self._agents[agent_id].status = status
            self._agents[agent_id].updated_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            agent_id: {
                "agent_id": agent.agent_id, "name": agent.name, "role": agent.role,
                "permission_level": agent.permission_level, "description": agent.description,
                "layer": agent.layer, "status": agent.status.value,
                "assigned_workflows": agent.assigned_workflows, "skills": agent.skills,
            }
            for agent_id, agent in self._agents.items()
        }


agent_registry = AgentRegistry()
