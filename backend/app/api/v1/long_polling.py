"""
HTTP 长轮询相关API
提供实时消息推送功能（替代WebSocket）
"""
from typing import Dict, Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
import asyncio

from app.dependencies import get_db
from app.services.message_service import MessageService
from app.services.conversation_service import ConversationService
from app.core.security import security
from app.core.exceptions import AuthenticationException
from app.core.permissions import get_current_user
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/poll", tags=["Long Polling"])

# 长轮询默认超时时间（秒）
DEFAULT_POLL_TIMEOUT = 30


class PollManager:
    """长轮询管理器"""

    def __init__(self):
        # 会话ID -> 等待事件的协程列表
        self.conversation_polls: Dict[int, List[asyncio.Event]] = {}
        # 轮询锁
        self._locks: Dict[int, asyncio.Lock] = {}

    def _get_lock(self, conversation_id: int) -> asyncio.Lock:
        """获取会话的锁"""
        if conversation_id not in self._locks:
            self._locks[conversation_id] = asyncio.Lock()
        return self._locks[conversation_id]

    async def wait_for_message(self, conversation_id: int, timeout: int = DEFAULT_POLL_TIMEOUT) -> Optional[Dict]:
        """
        等待会话中的新消息

        Args:
            conversation_id: 会话ID
            timeout: 超时时间（秒）

        Returns:
            新消息字典，如果没有新消息则返回 None
        """
        event = asyncio.Event()
        lock = self._get_lock(conversation_id)

        async with lock:
            if conversation_id not in self.conversation_polls:
                self.conversation_polls[conversation_id] = []
            self.conversation_polls[conversation_id].append(event)

        try:
            # 等待事件触发或超时
            await asyncio.wait_for(event.wait(), timeout=timeout)
            # 返回时说明有新消息，需要客户端重新请求获取
            return {"type": "new_message_available", "conversation_id": conversation_id}
        except asyncio.TimeoutError:
            return None
        finally:
            # 清理事件
            async with lock:
                if conversation_id in self.conversation_polls:
                    if event in self.conversation_polls[conversation_id]:
                        self.conversation_polls[conversation_id].remove(event)
                    if not self.conversation_polls[conversation_id]:
                        del self.conversation_polls[conversation_id]

    async def notify_new_message(self, conversation_id: int):
        """
        通知会话有新消息到来

        Args:
            conversation_id: 会话ID
        """
        lock = self._get_lock(conversation_id)
        async with lock:
            events = self.conversation_polls.get(conversation_id, []).copy()

        # 触发所有等待的事件
        for event in events:
            if not event.is_set():
                event.set()

        logger.info(f"通知会话 {conversation_id} 的 {len(events)} 个轮询有新消息")


# 创建全局轮询管理器
poll_manager = PollManager()


async def authenticate_request(token: Optional[str] = None) -> Dict:
    """
    认证HTTP请求

    Args:
        token: JWT token

    Returns:
        用户信息字典

    Raises:
        AuthenticationException: 认证失败
    """
    if not token:
        raise AuthenticationException("缺少认证token")

    try:
        payload = security.decode_token(token)
        user_id = payload.get("sub") or payload.get("user_id")
        if not user_id:
            raise AuthenticationException("无效的token")

        return {
            "id": int(user_id),
            "username": payload.get("username", ""),
            "role": payload.get("role", "patient"),
        }
    except Exception as e:
        raise AuthenticationException(f"认证失败: {e}")


async def verify_conversation_access(
    conversation_id: int,
    user_info: Dict,
    db: Session
) -> None:
    """
    验证用户对会话的访问权限

    Args:
        conversation_id: 会话ID
        user_info: 用户信息
        db: 数据库会话

    Raises:
        HTTPException: 无权访问
    """
    conversation = ConversationService.get_conversation_by_id(conversation_id, db)
    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")

    user_id = user_info["id"]
    user_role = user_info.get("role")

    if user_role == "patient":
        if conversation.patient_id != user_id:
            raise HTTPException(status_code=403, detail="无权访问该会话")
    elif user_role == "doctor":
        if conversation.doctor_id != user_id and conversation.doctor_id is not None:
            raise HTTPException(status_code=403, detail="无权访问该会话")


@router.post("/conversation/{conversation_id}")
async def poll_conversation_messages(
    conversation_id: int,
    last_message_id: Optional[int] = Query(None, description="最后收到的消息ID"),
    timeout: int = Query(DEFAULT_POLL_TIMEOUT, description="轮询超时时间（秒）"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    长轮询：获取会话新消息

    客户端发送请求携带 last_message_id，服务端等待新消息到来或超时后返回。
    如果有新消息，返回消息列表；否则返回超时。

    Args:
        conversation_id: 会话ID
        last_message_id: 客户端最后收到的消息ID
        timeout: 轮询超时时间（秒），最长60秒
        current_user: 当前用户信息
        db: 数据库会话

    Returns:
        消息列表或超时状态
    """
    user_info = current_user

    # 验证会话权限
    await verify_conversation_access(conversation_id, user_info, db)

    # 限制超时时间
    timeout = min(max(timeout, 1), 60)

    # 等待新消息或超时
    result = await poll_manager.wait_for_message(conversation_id, timeout)

    if result is None:
        # 超时，返回空列表
        return {
            "type": "timeout",
            "messages": [],
            "conversation_id": conversation_id,
        }

    # 有新消息，返回提示让客户端重新请求
    return {
        "type": "new_message",
        "messages": [],
        "conversation_id": conversation_id,
        "has_new": True,
    }


@router.get("/conversation/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: int,
    last_message_id: Optional[int] = Query(None, description="最后收到的消息ID，用于获取增量消息"),
    limit: int = Query(50, description="返回消息数量限制"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取会话消息

    获取指定会话的消息列表，支持增量获取（通过 last_message_id）。

    Args:
        conversation_id: 会话ID
        last_message_id: 客户端最后收到的消息ID，返回该消息之后的增量消息
        limit: 返回消息数量限制
        current_user: 当前用户信息
        db: 数据库会话

    Returns:
        消息列表
    """
    user_info = current_user

    # 验证会话权限
    await verify_conversation_access(conversation_id, user_info, db)

    # 获取消息 - 使用现有的 get_conversation_history 方法
    messages = MessageService.get_conversation_history(
        conversation_id=conversation_id,
        limit=limit,
        db=db,
    )

    # 如果提供了 last_message_id，筛选增量消息
    if last_message_id is not None:
        messages = [msg for msg in messages if msg.id > last_message_id]

    # 转换为字典格式
    message_list = []
    for msg in messages:
        message_list.append({
            "id": msg.id,
            "content": msg.content,
            "role": msg.role.value if hasattr(msg.role, 'value') else str(msg.role),
            "message_type": msg.message_type.value if hasattr(msg.message_type, 'value') else str(msg.message_type),
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
        })

    return {
        "messages": message_list,
        "conversation_id": conversation_id,
    }


# 辅助函数：发送消息通知
async def send_message_notification(message_id: int, conversation_id: int, db: Session):
    """
    发送消息通知（通过轮询）

    Args:
        message_id: 消息ID
        conversation_id: 会话ID
        db: 数据库会话
    """
    try:
        # 通知轮询管理器有新消息
        await poll_manager.notify_new_message(conversation_id)
        logger.info(f"消息通知已发送 - 消息ID: {message_id}, 会话ID: {conversation_id}")
    except Exception as e:
        logger.error(f"发送消息通知失败: {e}", exc_info=True)


# 导出
__all__ = ["router", "poll_manager", "send_message_notification"]
