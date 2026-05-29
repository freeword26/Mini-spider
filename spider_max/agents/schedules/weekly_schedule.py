"""
周排班配置 - 无人值守系统
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import time, datetime


@dataclass
class WeeklySlot:
    """周时间槽"""
    day_of_week: int  # 0=周一, 1=周二, ..., 6=周日
    time_str: str
    agent_id: str
    assigned_workflows: List[str] = field(default_factory=list)
    special_note: str = ""


@dataclass
class WeeklySchedule:
    """周排班"""
    start_date: str = ""
    slots: List[WeeklySlot] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.slots:
            self._initialize_default_slots()
    
    def _initialize_default_slots(self):
        """初始化默认周时间槽"""
        # 09:00 排班（周一到周五）
        for day in range(5):
            self.slots.append(WeeklySlot(
                day_of_week=day,
                time_str="09:00",
                agent_id="system-manager",
                assigned_workflows=["WF-003"],
                special_note="晨会"
            ))
        
        # 14:00 排班（周一到周五）
        for day in range(5):
            self.slots.append(WeeklySlot(
                day_of_week=day,
                time_str="14:00",
                agent_id="skill-manager",
                assigned_workflows=["WF-001", "WF-002"],
                special_note="任务协调"
            ))
        
        # 22:00 排班（周一到周五和周六）
        for day in range(5):
            self.slots.append(WeeklySlot(
                day_of_week=day,
                time_str="22:00",
                agent_id="learning-hacker",
                assigned_workflows=["WF-011"],
                special_note="文档处理"
            ))
        
        # 周六22:00 特别排班
        self.slots.append(WeeklySlot(
            day_of_week=5,
            time_str="22:00",
            agent_id="learning-hacker",
            assigned_workflows=["WF-014"],
            special_note="文档归档"
        ))
        
        # 02:00 排班（每天）
        for day in range(7):
            self.slots.append(WeeklySlot(
                day_of_week=day,
                time_str="02:00",
                agent_id="tech-expert",
                assigned_workflows=["WF-006"],
                special_note="数据库备份"
            ))
    
    def get_slots_for_day(self, day_of_week: int) -> List[WeeklySlot]:
        """获取指定周几的排班"""
        return [slot for slot in self.slots if slot.day_of_week == day_of_week]
    
    def get_current_week_slots(self) -> Dict[int, List[WeeklySlot]]:
        """获取本周所有排班"""
        result = {}
        for day in range(7):
            result[day] = self.get_slots_for_day(day)
        return result
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        day_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        return {
            "start_date": self.start_date,
            "slots": [
                {
                    "day": day_names[slot.day_of_week],
                    "day_of_week": slot.day_of_week,
                    "time": slot.time_str,
                    "agent_id": slot.agent_id,
                    "assigned_workflows": slot.assigned_workflows,
                    "special_note": slot.special_note
                }
                for slot in self.slots
            ]
        }


# 全局周排班实例
weekly_schedule = WeeklySchedule()
