"""
用药提醒相关的 Pydantic 模式
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from app.models.enums import ReminderType, ReminderStatus, ReminderFrequency


class ReminderBase(BaseModel):
    """提醒基础模式"""
    title: str = Field(..., max_length=200, description="提醒标题")
    reminder_type: ReminderType = Field(default=ReminderType.MEDICATION, description="提醒类型")
    medication_name: Optional[str] = Field(None, max_length=100, description="药物名称")
    dosage: Optional[str] = Field(None, max_length=50, description="剂量（如 500mg）")
    frequency: ReminderFrequency = Field(default=ReminderFrequency.DAILY, description="提醒频率")
    remind_time: Optional[str] = Field(None, max_length=20, description="提醒时间（如 08:00）")
    start_date: Optional[datetime] = Field(None, description="开始日期")
    end_date: Optional[datetime] = Field(None, description="结束日期")
    notes: Optional[str] = Field(None, description="备注")


class ReminderCreate(ReminderBase):
    """创建提醒请求模式"""
    pass


class ReminderUpdate(BaseModel):
    """更新提醒请求模式（所有字段可选）"""
    title: Optional[str] = Field(None, max_length=200, description="提醒标题")
    reminder_type: Optional[ReminderType] = Field(None, description="提醒类型")
    medication_name: Optional[str] = Field(None, max_length=100, description="药物名称")
    dosage: Optional[str] = Field(None, max_length=50, description="剂量")
    frequency: Optional[ReminderFrequency] = Field(None, description="提醒频率")
    remind_time: Optional[str] = Field(None, max_length=20, description="提醒时间")
    start_date: Optional[datetime] = Field(None, description="开始日期")
    end_date: Optional[datetime] = Field(None, description="结束日期")
    notes: Optional[str] = Field(None, description="备注")
    status: Optional[ReminderStatus] = Field(None, description="提醒状态")


class ReminderResponse(ReminderBase):
    """提醒响应模式"""
    id: int = Field(..., description="提醒ID")
    user_id: int = Field(..., description="用户ID")
    status: ReminderStatus = Field(..., description="提醒状态")
    last_reminded_at: Optional[datetime] = Field(None, description="最后提醒时间")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    model_config = ConfigDict(from_attributes=True)


class ReminderListResponse(BaseModel):
    """提醒列表响应"""
    items: list[ReminderResponse]
    total: int


# 导出
__all__ = [
    "ReminderBase",
    "ReminderCreate",
    "ReminderUpdate",
    "ReminderResponse",
    "ReminderListResponse",
]
