"""
消息相关的 Pydantic 模式
定义消息相关的请求和响应验证模式
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict


class MessageBase(BaseModel):
    """消息基础模式"""
    content: str = Field(..., min_length=1, description="消息内容")
    message_type: str = Field(default="text", description="消息类型：text/image/file/system")
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="扩展元数据",
    )


class MessageCreate(MessageBase):
    """创建消息请求模式"""
    conversation_id: int = Field(..., description="会话ID")
    role: str = Field(..., description="消息角色：user/assistant/system")
    file_url: Optional[str] = Field(None, max_length=500, description="文件URL")
    file_name: Optional[str] = Field(None, max_length=200, description="文件名")
    file_size: Optional[int] = Field(None, ge=0, description="文件大小（字节）")
    file_type: Optional[str] = Field(None, max_length=50, description="文件类型/MIME类型")
    agent_name: Optional[str] = Field(None, max_length=100, description="智能体名称")
    agent_id: Optional[str] = Field(None, max_length=100, description="智能体ID")
    # 使用 validation_alias 兼容前端传 metadata，使用 serialization_alias 兼容数据库字段 extra_metadata
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        validation_alias='metadata',
        serialization_alias='extra_metadata',
        description="扩展元数据",
    )


class MessageUpdate(BaseModel):
    """更新消息请求模式（所有字段可选）"""
    content: Optional[str] = Field(None, min_length=1, description="消息内容")
    is_read: Optional[bool] = Field(None, description="是否已读")
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        validation_alias='metadata',
        serialization_alias='extra_metadata',
        description="扩展元数据",
    )


class MessageResponse(MessageBase):
    """消息响应模式"""
    id: int = Field(..., description="消息ID")
    conversation_id: int = Field(..., description="会话ID")
    user_id: Optional[int] = Field(None, description="用户ID")
    role: str = Field(..., description="消息角色")
    file_url: Optional[str] = Field(None, description="文件URL")
    file_name: Optional[str] = Field(None, description="文件名")
    file_size: Optional[int] = Field(None, description="文件大小（字节）")
    file_type: Optional[str] = Field(None, description="文件类型/MIME类型")
    agent_name: Optional[str] = Field(None, description="智能体名称")
    agent_id: Optional[str] = Field(None, description="智能体ID")
    # 使用 validation_alias 读取数据库字段 extra_metadata，使用 serialization_alias 输出为 metadata
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        validation_alias='extra_metadata',
        serialization_alias='metadata',
        description="扩展元数据",
    )
    is_read: bool = Field(default=False, description="是否已读")
    is_edited: bool = Field(default=False, description="是否已编辑")
    edited_at: Optional[datetime] = Field(None, description="编辑时间")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    model_config = ConfigDict(from_attributes=True)


class MessageListResponse(BaseModel):
    """消息列表响应模式"""
    total: int = Field(..., description="总数量")
    items: List[MessageResponse] = Field(..., description="消息列表")


class MessageReadUpdate(BaseModel):
    """标记消息已读请求模式"""
    message_ids: List[int] = Field(..., min_items=1, description="消息ID列表")


class MessageSend(BaseModel):
    """发送消息请求模式（用于WebSocket或API）"""
    conversation_id: int = Field(..., description="会话ID")
    content: str = Field(..., min_length=1, description="消息内容")
    message_type: str = Field(default="text", description="消息类型")
    file_url: Optional[str] = Field(None, description="文件URL（如果是文件消息）")
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        validation_alias='metadata',
        serialization_alias='extra_metadata',
        description="扩展元数据",
    )


# 导出
__all__ = [
    "MessageBase",
    "MessageCreate",
    "MessageUpdate",
    "MessageResponse",
    "MessageListResponse",
    "MessageReadUpdate",
    "MessageSend",
]

