"""
每日排班配置 - 无人值守系统
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import time


@dataclass
class TimeSlot:
    """时间槽"""
    start_time: time
    end_time: time
    agent_id: str
    assigned_workflows: List[str] = field(default_factory=list)
    other_duties: List[str] = field(default_factory=list)


@dataclass
class DailySchedule:
    """每日排班"""
    date: str = ""
    time_slots: List[TimeSlot] = field(default_factory=list)
    always_on_agents: List[Dict] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.time_slots:
            self._initialize_default_slots()
        if not self.always_on_agents:
            self._initialize_always_on_agents()
    
    def _initialize_default_slots(self):
        """初始化默认时间槽"""
        self.time_slots = [
            TimeSlot(
                start_time=time(0, 0),
                end_time=time(8, 0),
                agent_id="tech-expert",
                assigned_workflows=["WF-006", "WF-LIFECYCLE-DAILY"],
                other_duties=["系统监控", "日志清理", "生命周期扫描"]
            ),
            TimeSlot(
                start_time=time(8, 0),
                end_time=time(12, 0),
                agent_id="system-manager",
                assigned_workflows=["WF-003", "WF-002"],
                other_duties=["晨会报告", "系统巡检"]
            ),
            TimeSlot(
                start_time=time(12, 0),
                end_time=time(18, 0),
                agent_id="skill-manager",
                assigned_workflows=["WF-001", "WF-002"],
                other_duties=["术语生成", "任务协调"]
            ),
            TimeSlot(
                start_time=time(18, 0),
                end_time=time(23, 59),
                agent_id="learning-hacker",
                assigned_workflows=["WF-004", "WF-011", "WF-012", "WF-013"],
                other_duties=["日报生成", "文档处理"]
            )
        ]
    
    def _initialize_always_on_agents(self):
        """初始化全天候Agent"""
        self.always_on_agents = [
            {
                "agent_id": "data-scientist",
                "assigned_workflows": ["WF-001", "WF-005"],
                "other_duties": ["数据同步", "合规检查"]
            },
            {
                "agent_id": "expert-biz-doctor",
                "assigned_workflows": ["WF-005"],
                "other_duties": ["合规检查", "业务审查"]
            }
        ]
    
    def get_current_slot(self, current_time: time) -> Optional[TimeSlot]:
        """获取当前时间槽"""
        for slot in self.time_slots:
            if slot.start_time <= current_time < slot.end_time:
                return slot
        
        # 检查23:00-24:00的特殊情况
        last_slot = self.time_slots[-1]
        if last_slot and current_time >= last_slot.start_time:
            return last_slot
        
        return None
    
    def get_on_duty_agents(self, current_time: time) -> List[str]:
        """获取当前当班的Agent"""
        agents = []
        
        # 检查时间槽Agent
        current_slot = self.get_current_slot(current_time)
        if current_slot:
            agents.append(current_slot.agent_id)
        
        # 添加全天候Agent
        agents.extend([agent["agent_id"] for agent in self.always_on_agents])
        
        return agents
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "date": self.date,
            "time_slots": [
                {
                    "start_time": slot.start_time.strftime("%H:%M"),
                    "end_time": slot.end_time.strftime("%H:%M"),
                    "agent_id": slot.agent_id,
                    "assigned_workflows": slot.assigned_workflows,
                    "other_duties": slot.other_duties
                }
                for slot in self.time_slots
            ],
            "always_on_agents": self.always_on_agents
        }


# 全局每日排班实例
daily_schedule = DailySchedule()
