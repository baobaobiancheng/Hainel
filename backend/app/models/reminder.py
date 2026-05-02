"""
用药提醒模型
定义用药/检查/复诊提醒相关的数据库模型
"""
from sqlalchemy import Column, String, Enum as SQLEnum, DateTime, Text, Integer, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import BaseModel
from app.models.enums import ReminderType, ReminderStatus, ReminderFrequency


class Reminder(BaseModel):
    """提醒模型"""

    __tablename__ = "reminders"

    # 关联用户
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="用户ID",
    )

    # 提醒类型
    reminder_type = Column(
        SQLEnum(ReminderType, values_callable=lambda x: [e.value for e in x]),
        default=ReminderType.MEDICATION,
        nullable=False,
        index=True,
        comment="提醒类型：medication/examination/follow_up",
    )

    # 基本信息
    title = Column(String(200), nullable=False, comment="提醒标题")
    medication_name = Column(String(100), nullable=True, comment="药物名称")
    dosage = Column(String(50), nullable=True, comment="剂量")
    frequency = Column(
        SQLEnum(ReminderFrequency, values_callable=lambda x: [e.value for e in x]),
        default=ReminderFrequency.DAILY,
        nullable=False,
        comment="提醒频率",
    )
    remind_time = Column(String(20), nullable=True, comment="提醒时间（如 08:00）")
    start_date = Column(DateTime, nullable=True, comment="开始日期")
    end_date = Column(DateTime, nullable=True, comment="结束日期")
    notes = Column(Text, nullable=True, comment="备注")

    # 状态
    status = Column(
        SQLEnum(ReminderStatus, values_callable=lambda x: [e.value for e in x]),
        default=ReminderStatus.ACTIVE,
        nullable=False,
        index=True,
        comment="提醒状态：active/paused/completed/cancelled",
    )
    last_reminded_at = Column(DateTime, nullable=True, comment="最后提醒时间")

    # 关系
    user = relationship("User", foreign_keys=[user_id])

    def __repr__(self) -> str:
        return f"<Reminder(id={self.id}, user_id={self.user_id}, title={self.title})>"


# 导出
__all__ = ["Reminder"]
