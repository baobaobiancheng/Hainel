"""
WebSocket 连接管理器
管理所有WebSocket连接，实现消息推送功能
"""
from typing import Dict, Set, Optional, List, Any
from fastapi import WebSocket
from dataclasses import dataclass, field
from datetime import datetime
import json
import asyncio

from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ConnectionInfo:
    """连接信息"""
    websocket: WebSocket
    user_id: int
    user_role: str  # patient, doctor
    conversation_id: Optional[int] = None
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)


class WebSocketManager:
    """
    WebSocket连接管理器

    功能：
    - 管理用户WebSocket连接
    - 管理会话级别的连接
    - 消息广播和推送
    - 心跳保活
    """

    def __init__(self):
        # user_id -> ConnectionInfo
        self.user_connections: Dict[int, ConnectionInfo] = {}

        # conversation_id -> Set[ConnectionInfo]
        self.conversation_connections: Dict[int, Set[ConnectionInfo]] = {}

        # 定期清理超时连接任务
        self._cleanup_task: Optional[asyncio.Task] = None

    async def connect(
        self,
        websocket: WebSocket,
        user_id: int,
        user_role: str,
        conversation_id: Optional[int] = None
    ) -> ConnectionInfo:
        """
        建立WebSocket连接

        Args:
            websocket: WebSocket连接对象
            user_id: 用户ID
            user_role: 用户角色
            conversation_id: 会话ID（可选）

        Returns:
            ConnectionInfo: 连接信息
        """
        conn_info = ConnectionInfo(
            websocket=websocket,
            user_id=user_id,
            user_role=user_role,
            conversation_id=conversation_id
        )

        # 保存用户连接
        self.user_connections[user_id] = conn_info

        # 如果有会话ID，添加到会话连接集合
        if conversation_id is not None:
            if conversation_id not in self.conversation_connections:
                self.conversation_connections[conversation_id] = set()
            self.conversation_connections[conversation_id].add(conn_info)

        logger.info(f"WebSocket连接建立: user_id={user_id}, role={user_role}, conversation_id={conversation_id}")

        return conn_info

    async def register_connection(
        self,
        websocket: WebSocket,
        user_id: int,
        user_role: str,
        conversation_id: Optional[int] = None
    ) -> ConnectionInfo:
        """
        注册WebSocket连接（不调用accept，用于已接受的连接）

        Args:
            websocket: WebSocket连接对象
            user_id: 用户ID
            user_role: 用户角色
            conversation_id: 会话ID（可选）

        Returns:
            ConnectionInfo: 连接信息
        """
        conn_info = ConnectionInfo(
            websocket=websocket,
            user_id=user_id,
            user_role=user_role,
            conversation_id=conversation_id
        )

        # 保存用户连接
        self.user_connections[user_id] = conn_info

        # 如果有会话ID，添加到会话连接集合
        if conversation_id is not None:
            if conversation_id not in self.conversation_connections:
                self.conversation_connections[conversation_id] = set()
            self.conversation_connections[conversation_id].add(conn_info)

        logger.info(f"WebSocket连接注册: user_id={user_id}, role={user_role}, conversation_id={conversation_id}")

        return conn_info

    async def disconnect(
        self,
        user_id: int,
        conversation_id: Optional[int] = None
    ):
        """
        断开WebSocket连接

        Args:
            user_id: 用户ID
            conversation_id: 会话ID（可选）
        """
        conn_info = self.user_connections.pop(user_id, None)

        if conn_info and conversation_id and conversation_id in self.conversation_connections:
            self.conversation_connections[conversation_id].discard(conn_info)

            # 如果会话没有连接了，清理
            if not self.conversation_connections[conversation_id]:
                del self.conversation_connections[conversation_id]

        logger.info(f"WebSocket连接断开: user_id={user_id}")

    async def send_personal_message(
        self,
        message: Dict[str, Any],
        user_id: int
    ) -> bool:
        """
        发送消息给指定用户

        Args:
            message: 消息内容
            user_id: 目标用户ID

        Returns:
            bool: 是否发送成功
        """
        logger.info(f"[WebSocket] 尝试发送消息给用户 {user_id}, 当前在线用户: {list(self.user_connections.keys())}")
        conn_info = self.user_connections.get(user_id)

        if conn_info is None:
            logger.warning(f"用户 {user_id} 不在线，无法发送消息")
            return False

        try:
            await conn_info.websocket.send_text(json.dumps(message, ensure_ascii=False))
            return True
        except Exception as e:
            logger.error(f"发送消息给用户 {user_id} 失败: {e}")
            await self.disconnect(user_id)
            return False

    async def broadcast_to_conversation(
        self,
        message: Dict[str, Any],
        conversation_id: int,
        exclude_user_ids: Optional[List[int]] = None
    ) -> int:
        """
        向会话中的所有连接广播消息

        Args:
            message: 消息内容
            conversation_id: 会话ID
            exclude_user_ids: 排除的用户ID列表

        Returns:
            int: 成功发送的数量
        """
        if conversation_id not in self.conversation_connections:
            logger.warning(f"会话 {conversation_id} 没有在线连接")
            return 0

        connections = self.conversation_connections[conversation_id]
        exclude_set = set(exclude_user_ids or [])
        success_count = 0

        for conn_info in connections.copy():
            if conn_info.user_id in exclude_set:
                continue

            try:
                await conn_info.websocket.send_text(json.dumps(message, ensure_ascii=False))
                success_count += 1
            except Exception as e:
                logger.error(f"广播消息给用户 {conn_info.user_id} 失败: {e}")
                await self.disconnect(conn_info.user_id)

        return success_count

    async def broadcast_to_role(
        self,
        message: Dict[str, Any],
        role: str
    ) -> int:
        """
        向指定角色的所有在线用户广播消息

        Args:
            message: 消息内容
            role: 目标角色 (patient/doctor)

        Returns:
            int: 成功发送的数量
        """
        success_count = 0

        for user_id, conn_info in self.user_connections.items():
            if conn_info.user_role == role:
                try:
                    await conn_info.websocket.send_text(json.dumps(message, ensure_ascii=False))
                    success_count += 1
                except Exception as e:
                    logger.error(f"广播消息给用户 {user_id} 失败: {e}")
                    await self.disconnect(user_id)

        return success_count

    def is_user_online(self, user_id: int) -> bool:
        """检查用户是否在线"""
        return user_id in self.user_connections

    def get_online_users(self, role: Optional[str] = None) -> List[int]:
        """
        获取在线用户列表

        Args:
            role: 角色过滤（可选）

        Returns:
            List[int]: 在线用户ID列表
        """
        if role:
            return [
                user_id for user_id, conn_info in self.user_connections.items()
                if conn_info.user_role == role
            ]
        return list(self.user_connections.keys())

    def get_connection_count(self) -> int:
        """获取当前连接总数"""
        return len(self.user_connections)


# 创建全局WebSocket管理器
ws_manager = WebSocketManager()


# 导出
__all__ = ["WebSocketManager", "ws_manager", "ConnectionInfo"]
