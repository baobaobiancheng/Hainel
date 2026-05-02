"""
消息模型
定义会话消息相关的数据库模型
"""
from datetime import datetime
from enum import Enum
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Enum as SQLEnum,
    DateTime,
    ForeignKey,
    JSON,
    Boolean,
    Index,
)
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class MessageType(str, Enum):
    """消息类型枚举"""
    TEXT = "text"  # 文本消息
    IMAGE = "image"  # 图片消息
    FILE = "file"  # 文件消息
    SYSTEM = "system"  # 系统消息


class MessageRole(str, Enum):
    """消息角色枚举（值与数据库 ENUM 一致：大写）"""
    USER = "USER"  # 用户（患者或医生）
    ASSISTANT = "ASSISTANT"  # 智能体助手
    SYSTEM = "SYSTEM"  # 系统


class Message(BaseModel):
    """消息模型"""
    
    __tablename__ = "messages"
    
    # 关联会话
    conversation_id = Column(
        Integer,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="会话ID",
    )
    
    # 关联用户（可选，系统消息可能没有用户）
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="用户ID（发送者）",
    )
    
    # 消息基本信息
    role = Column(
        SQLEnum(MessageRole),
        nullable=False,
        index=True,
        comment="消息角色：user/assistant/system",
    )
    message_type = Column(
        SQLEnum(MessageType, values_callable=lambda obj: [e.value for e in obj]),
        default=MessageType.TEXT,
        nullable=False,
        comment="消息类型：text/image/file/system",
    )
    
    # 消息内容
    content = Column(Text, nullable=False, comment="消息内容")
    
    # 文件相关（如果是文件或图片消息）
    file_url = Column(String(500), nullable=True, comment="文件URL")
    file_name = Column(String(200), nullable=True, comment="文件名")
    file_size = Column(Integer, nullable=True, comment="文件大小（字节）")
    file_type = Column(String(50), nullable=True, comment="文件类型/MIME类型")
    
    # 智能体相关
    agent_name = Column(String(100), nullable=True, index=True, comment="智能体名称")
    agent_id = Column(String(100), nullable=True, index=True, comment="智能体ID")
    
    # 消息元数据
    extra_metadata = Column(JSON, nullable=True, comment="扩展元数据（如OCR结果、结构化数据等）")
    
    # 状态
    is_read = Column(Boolean, default=False, nullable=False, comment="是否已读")
    is_edited = Column(Boolean, default=False, nullable=False, comment="是否已编辑")
    
    # 编辑时间
    edited_at = Column(DateTime, nullable=True, comment="编辑时间")
    
    # 关系
    conversation = relationship(
        "Conversation",
        back_populates="messages",
    )
    user = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="messages",
    )
    
    # 索引
    __table_args__ = (
        Index("idx_message_conversation_created", "conversation_id", "created_at"),
        Index("idx_message_user_created", "user_id", "created_at"),
        Index("idx_message_agent_created", "agent_id", "created_at"),
    )
    
    def __repr__(self) -> str:
        """返回消息的字符串表示"""
        return f"<Message(id={self.id}, conversation_id={self.conversation_id}, role={self.role})>"
    
    def mark_as_read(self):
        """标记消息为已读"""
        self.is_read = True
    
    def mark_as_edited(self):
        """标记消息为已编辑"""
        self.is_edited = True
        self.edited_at = datetime.utcnow()
    
    def is_from_user(self) -> bool:
        """检查消息是否来自用户"""
        return self.role == MessageRole.USER
    
    def is_from_assistant(self) -> bool:
        """检查消息是否来自智能体"""
        return self.role == MessageRole.ASSISTANT
    
    def is_system_message(self) -> bool:
        """检查消息是否为系统消息"""
        return self.role == MessageRole.SYSTEM


# 导出
__all__ = [
    "Message",
    "MessageType",
    "MessageRole",
]

