"""
公共枚举定义
供多个模型共享使用的枚举类型
"""
from enum import Enum


class ReminderType(str, Enum):
    """提醒类型"""
    MEDICATION = "medication"      # 用药提醒
    EXAMINATION = "examination"    # 检查提醒
    FOLLOW_UP = "follow_up"        # 复诊提醒


class ReminderStatus(str, Enum):
    """提醒状态"""
    ACTIVE = "active"          # 激活
    PAUSED = "paused"          # 暂停
    COMPLETED = "completed"    # 已完成
    CANCELLED = "cancelled"    # 已取消


class ReminderFrequency(str, Enum):
    """提醒频率"""
    ONCE = "once"                          # 一次性
    DAILY = "daily"                        # 每天一次
    TWICE_DAILY = "twice_daily"            # 每天两次
    THREE_TIMES_DAILY = "three_times_daily"  # 每天三次
    WEEKLY = "weekly"                      # 每周
    CUSTOM = "custom"                      # 自定义


# 导出
__all__ = ["ReminderType", "ReminderStatus", "ReminderFrequency"]
