"""
Schedules模块 - 无人值守系统
"""

try:
    from .daily_schedule import (
        TimeSlot,
        DailySchedule,
        daily_schedule
    )
    from .weekly_schedule import (
        WeeklySlot,
        WeeklySchedule,
        weekly_schedule
    )
except (ImportError, SystemError):
    from daily_schedule import (
        TimeSlot,
        DailySchedule,
        daily_schedule
    )
    from weekly_schedule import (
        WeeklySlot,
        WeeklySchedule,
        weekly_schedule
    )

__all__ = [
    "TimeSlot",
    "DailySchedule",
    "daily_schedule",
    "WeeklySlot",
    "WeeklySchedule",
    "weekly_schedule"
]
