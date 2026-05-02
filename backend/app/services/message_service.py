"""
消息服务
提供消息相关的业务逻辑处理
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.message import Message, MessageType, MessageRole
from app.schemas.message import (
    MessageCreate,
    MessageUpdate,
    MessageReadUpdate,
)
from app.core.exceptions import (
    NotFoundException,
    ValidationException,
)
from app.services.conversation_service import ConversationService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MessageService:
    """消息服务类"""
    
    @staticmethod
    def create_message(
        message_data: MessageCreate,
        user_id: Optional[int] = None,
        db: Session = None,
    ) -> Message:
        """
        创建新消息
        
        Args:
            message_data: 消息创建数据
            db: 数据库会话
        
        Returns:
            创建的消息对象
        
        Raises:
            NotFoundException: 会话不存在
            ValidationException: 无效的消息类型或角色
        """
        # 验证会话是否存在
        conversation = ConversationService.get_conversation_by_id(
            message_data.conversation_id, db
        )
        if not conversation:
            raise NotFoundException(f"会话 ID {message_data.conversation_id} 不存在")
        
        # 验证消息类型
        try:
            message_type = MessageType(message_data.message_type)
        except ValueError:
            raise ValidationException(f"无效的消息类型: {message_data.message_type}")
        
        # 验证消息角色（兼容前端传 "user"/"USER"，统一转为大写与 DB 枚举一致）
        try:
            role = MessageRole(message_data.role.strip().upper())
        except ValueError:
            raise ValidationException(f"无效的消息角色: {message_data.role}")
        
        # 创建消息对象
        # 注意：MessageCreate schema 中没有 user_id 字段，需要从外部传入
        message = Message(
            conversation_id=message_data.conversation_id,
            user_id=user_id,  # user_id 从参数传入
            role=role,
            message_type=message_type,
            content=message_data.content,
            file_url=message_data.file_url,
            file_name=message_data.file_name,
            file_size=message_data.file_size,
            file_type=message_data.file_type,
            agent_name=message_data.agent_name,
            agent_id=message_data.agent_id,
            extra_metadata=message_data.metadata,
        )
        
        db.add(message)
        
        # 更新会话的消息计数和最后消息时间
        ConversationService.increment_message_count(message_data.conversation_id, db)
        
        db.commit()
        db.refresh(message)
        
        logger.info(f"创建消息成功: ID {message.id}, 会话 ID {message.conversation_id}")
        return message
    
    @staticmethod
    def get_message_by_id(message_id: int, db: Session) -> Optional[Message]:
        """
        根据ID获取消息
        
        Args:
            message_id: 消息ID
            db: 数据库会话
        
        Returns:
            消息对象，如果不存在返回None
        """
        return db.query(Message).filter(Message.id == message_id).first()
    
    @staticmethod
    def update_message(
        message_id: int,
        message_data: MessageUpdate,
        db: Session,
    ) -> Message:
        """
        更新消息
        
        Args:
            message_id: 消息ID
            message_data: 消息更新数据
            db: 数据库会话
        
        Returns:
            更新后的消息对象
        
        Raises:
            NotFoundException: 消息不存在
        """
        message = MessageService.get_message_by_id(message_id, db)
        if not message:
            raise NotFoundException(f"消息 ID {message_id} 不存在")
        
        # 更新字段
        update_dict = message_data.model_dump(exclude_unset=True)
        
        # 如果更新内容，标记为已编辑
        if "content" in update_dict:
            message.mark_as_edited()
        
        message.update_from_dict(update_dict)
        db.commit()
        db.refresh(message)
        
        logger.info(f"更新消息成功: ID {message.id}")
        return message
    
    @staticmethod
    def delete_message(message_id: int, db: Session) -> bool:
        """
        删除消息
        
        Args:
            message_id: 消息ID
            db: 数据库会话
        
        Returns:
            是否删除成功
        
        Raises:
            NotFoundException: 消息不存在
        """
        message = MessageService.get_message_by_id(message_id, db)
        if not message:
            raise NotFoundException(f"消息 ID {message_id} 不存在")
        
        conversation_id = message.conversation_id
        
        db.delete(message)
        
        # 更新会话的消息计数
        conversation = ConversationService.get_conversation_by_id(conversation_id, db)
        if conversation:
            conversation.message_count = max(0, conversation.message_count - 1)
        
        db.commit()
        
        logger.info(f"删除消息成功: ID {message_id}")
        return True
    
    @staticmethod
    def list_messages(
        conversation_id: int,
        skip: int = 0,
        limit: int = 100,
        role: Optional[MessageRole] = None,
        message_type: Optional[MessageType] = None,
        agent_id: Optional[str] = None,
        db: Session = None,
    ) -> tuple[List[Message], int]:
        """
        获取会话的消息列表
        
        Args:
            conversation_id: 会话ID
            skip: 跳过的记录数
            limit: 返回的记录数
            role: 消息角色过滤
            message_type: 消息类型过滤
            agent_id: 智能体ID过滤
            db: 数据库会话
        
        Returns:
            (消息列表, 总数量)
        
        Raises:
            NotFoundException: 会话不存在
        """
        # 验证会话是否存在
        conversation = ConversationService.get_conversation_by_id(conversation_id, db)
        if not conversation:
            raise NotFoundException(f"会话 ID {conversation_id} 不存在")
        
        query = db.query(Message).filter(Message.conversation_id == conversation_id)
        
        if role:
            query = query.filter(Message.role == role)
        
        if message_type:
            query = query.filter(Message.message_type == message_type)
        
        if agent_id:
            query = query.filter(Message.agent_id == agent_id)
        
        total = query.count()
        
        messages = (
            query.order_by(Message.created_at)
            .offset(skip)
            .limit(limit)
            .all()
        )
        
        return messages, total
    
    @staticmethod
    def mark_as_read(message_id: int, db: Session) -> Message:
        """
        标记消息为已读
        
        Args:
            message_id: 消息ID
            db: 数据库会话
        
        Returns:
            更新后的消息对象
        
        Raises:
            NotFoundException: 消息不存在
        """
        message = MessageService.get_message_by_id(message_id, db)
        if not message:
            raise NotFoundException(f"消息 ID {message_id} 不存在")
        
        message.mark_as_read()
        db.commit()
        db.refresh(message)
        
        logger.debug(f"标记消息已读: ID {message_id}")
        return message
    
    @staticmethod
    def mark_messages_as_read(
        read_data: MessageReadUpdate,
        db: Session,
    ) -> List[Message]:
        """
        批量标记消息为已读
        
        Args:
            read_data: 已读更新数据
            db: 数据库会话
        
        Returns:
            更新后的消息列表
        """
        messages = []
        for message_id in read_data.message_ids:
            try:
                message = MessageService.mark_as_read(message_id, db)
                messages.append(message)
            except NotFoundException:
                logger.warning(f"消息 ID {message_id} 不存在，跳过")
                continue
        
        logger.info(f"批量标记消息已读: {len(messages)} 条消息")
        return messages
    
    @staticmethod
    def get_unread_count(
        conversation_id: int,
        user_id: Optional[int] = None,
        db: Session = None,
    ) -> int:
        """
        获取未读消息数量
        
        Args:
            conversation_id: 会话ID
            user_id: 用户ID（可选，如果提供则只统计该用户未读的消息）
            db: 数据库会话
        
        Returns:
            未读消息数量
        """
        query = db.query(Message).filter(
            and_(
                Message.conversation_id == conversation_id,
                Message.is_read == False,
            )
        )
        
        # 如果指定了用户ID，只统计不是该用户发送的消息
        if user_id:
            query = query.filter(Message.user_id != user_id)
        
        return query.count()
    
    @staticmethod
    def get_conversation_history(
        conversation_id: int,
        limit: int = 100,
        db: Session = None,
    ) -> List[Message]:
        """
        获取会话的完整历史消息（用于构建对话上下文）
        
        Args:
            conversation_id: 会话ID
            limit: 最大消息数量
            db: 数据库会话
        
        Returns:
            消息列表（按时间正序）
        """
        messages, _ = MessageService.list_messages(
            conversation_id=conversation_id,
            skip=0,
            limit=limit,
            db=db,
        )
        return messages


# 创建全局服务实例
message_service = MessageService()


# 导出
__all__ = ["MessageService", "message_service"]

