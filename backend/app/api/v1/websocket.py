"""
WebSocket API
提供WebSocket连接接口，支持患者端和医生端
"""
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel
import json
from datetime import datetime

from app.core.websocket_manager import ws_manager
from app.core.security import security
from app.core.exceptions import AuthenticationException
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["WebSocket"])


class AuthMessage(BaseModel):
    """认证消息"""
    type: str = "auth"
    token: str


class StatusUpdateMessage(BaseModel):
    """状态更新消息"""
    type: str = "status_update"
    conversation_id: int
    status: str
    message: str
    data: Optional[dict] = None


async def authenticate_websocket(websocket: WebSocket) -> dict:
    """
    WebSocket认证

    Args:
        websocket: WebSocket连接

    Returns:
        用户信息字典

    Raises:
        AuthenticationException: 认证失败
    """
    # 从查询参数获取token
    token = websocket.query_params.get("token")

    if not token:
        # 尝试从第一条消息获取token
        try:
            # 这里需要客户端先发送认证消息
            return {"id": 0, "role": "unknown", "authenticated": False}
        except:
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
            "authenticated": True
        }
    except Exception as e:
        logger.error(f"WebSocket认证失败: {e}")
        raise AuthenticationException(f"认证失败: {e}")


@router.websocket("/consultation")
async def websocket_patient_consultation(
    websocket: WebSocket,
    conversation_id: Optional[int] = Query(None, description="会话ID")
):
    """
    患者端WebSocket连接

    用于接收咨询状态推送：
    - analyzing: 智能分析中
    - completed: 智能分析结果已生成
    - reviewing: 医生审核中
    - completed: 诊断完成

    Args:
        conversation_id: 会话ID（可选）
    """
    user_info = None
    user_id = None

    try:
        # 第一步：接受WebSocket连接
        await websocket.accept()

        # 第二步：接收认证消息
        try:
            auth_data = await websocket.receive_text()
            auth_msg = json.loads(auth_data)

            if auth_msg.get("type") == "auth":
                token = auth_msg.get("token")
                if not token:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "缺少token"
                    }))
                    await websocket.close()
                    return

                # 验证token
                try:
                    payload = security.decode_token(token)
                    user_id = int(payload.get("sub") or payload.get("user_id"))
                    user_info = {
                        "id": user_id,
                        "role": payload.get("role", "patient"),
                        "authenticated": True
                    }
                except Exception as e:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": f"认证失败: {e}"
                    }))
                    await websocket.close()
                    return
            else:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "第一条消息必须是认证消息"
                }))
                await websocket.close()
                return
        except WebSocketDisconnect:
            return
        except Exception as e:
            logger.error(f"接收认证消息失败: {e}")
            await websocket.close()
            return

        # 第三步：注册连接（不再调用accept，因为已经接受过了）
        await ws_manager.register_connection(
            websocket=websocket,
            user_id=user_id,
            user_role=user_info.get("role", "patient"),
            conversation_id=conversation_id
        )

        # 发送连接成功消息
        await websocket.send_text(json.dumps({
            "type": "connected",
            "message": "连接成功",
            "user_id": user_id
        }))

        # 第三步：保持连接，处理消息
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                # 处理心跳
                if message.get("type") == "heartbeat":
                    # 从ws_manager获取连接信息
                    conn_info = ws_manager.user_connections.get(user_id)
                    if conn_info:
                        conn_info.last_heartbeat = datetime.utcnow()
                    await websocket.send_text(json.dumps({
                        "type": "heartbeat_ack",
                        "timestamp": datetime.utcnow().isoformat()
                    }))

                # 处理其他消息
                elif message.get("type") == "ping":
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    }))

            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                logger.warning(f"收到无效的JSON消息")
            except Exception as e:
                logger.error(f"处理WebSocket消息失败: {e}")
                break

    except WebSocketDisconnect:
        logger.info(f"患者端WebSocket断开: user_id={user_id}")
    except Exception as e:
        logger.error(f"患者端WebSocket错误: {e}")
    finally:
        if user_id:
            await ws_manager.disconnect(user_id, conversation_id)


@router.websocket("/doctor")
async def websocket_doctor(
    websocket: WebSocket
):
    """
    医生端WebSocket连接

    用于接收：
    - new_session: 新会话分配通知
    - session_update: 会话状态更新
    """
    user_info = None
    user_id = None

    try:
        # 第一步：接受WebSocket连接
        await websocket.accept()

        # 第二步：接收认证消息
        try:
            auth_data = await websocket.receive_text()
            auth_msg = json.loads(auth_data)

            if auth_msg.get("type") == "auth":
                token = auth_msg.get("token")
                if not token:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "缺少token"
                    }))
                    await websocket.close()
                    return

                # 验证token
                try:
                    payload = security.decode_token(token)
                    user_id = int(payload.get("sub") or payload.get("user_id"))
                    role = payload.get("role", "patient")

                    if role != "doctor" and role != "admin":
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "message": "只有医生可以连接此端点"
                        }))
                        await websocket.close()
                        return

                    user_info = {
                        "id": user_id,
                        "role": role,
                        "authenticated": True
                    }
                except Exception as e:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": f"认证失败: {e}"
                    }))
                    await websocket.close()
                    return
            else:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "第一条消息必须是认证消息"
                }))
                await websocket.close()
                return
        except WebSocketDisconnect:
            return
        except Exception as e:
            logger.error(f"接收认证消息失败: {e}")
            await websocket.close()
            return

        # 第三步：注册连接（不再调用accept，因为已经接受过了）
        await ws_manager.register_connection(
            websocket=websocket,
            user_id=user_id,
            user_role="doctor"
        )

        # 发送连接成功消息
        await websocket.send_text(json.dumps({
            "type": "connected",
            "message": "医生端连接成功",
            "user_id": user_id
        }))

        # 第三步：保持连接，处理消息
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                # 处理心跳
                if message.get("type") == "heartbeat":
                    # 从ws_manager获取连接信息
                    conn_info = ws_manager.user_connections.get(user_id)
                    if conn_info:
                        conn_info.last_heartbeat = datetime.utcnow()
                    await websocket.send_text(json.dumps({
                        "type": "heartbeat_ack",
                        "timestamp": datetime.utcnow().isoformat()
                    }))

                # 处理其他消息
                elif message.get("type") == "ping":
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    }))

            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                logger.warning(f"收到无效的JSON消息")
            except Exception as e:
                logger.error(f"处理WebSocket消息失败: {e}")
                break

    except WebSocketDisconnect:
        logger.info(f"医生端WebSocket断开: user_id={user_id}")
    except Exception as e:
        logger.error(f"医生端WebSocket错误: {e}")
    finally:
        if user_id:
            await ws_manager.disconnect(user_id)


# 辅助函数：推送状态更新
async def push_status_update(
    conversation_id: int,
    patient_id: int,
    status: str,
    message: str,
    data: Optional[dict] = None
):
    """
    向患者推送状态更新

    Args:
        conversation_id: 会话ID
        patient_id: 患者ID
        status: 状态值
        message: 状态消息
        data: 附加数据
    """
    await ws_manager.send_personal_message(
        message={
            "type": "status_update",
            "conversation_id": conversation_id,
            "status": status,
            "message": message,
            "data": data or {}
        },
        user_id=patient_id
    )


# 辅助函数：推送给医生
async def push_to_doctor(
    doctor_id: int,
    message_type: str,
    data: dict
):
    """
    向医生推送消息

    Args:
        doctor_id: 医生ID
        message_type: 消息类型
        data: 消息数据
    """
    await ws_manager.send_personal_message(
        message={
            "type": message_type,
            **data
        },
        user_id=doctor_id
    )


# 辅助函数：广播新会话给医生
async def broadcast_new_session(
    conversation_id: int,
    patient_id: int,
    chief_complaint: str,
    department: str
):
    """
    向所有在线医生广播新会话

    Args:
        conversation_id: 会话ID
        patient_id: 患者ID
        chief_complaint: 主诉
        department: 建议科室
    """
    await ws_manager.broadcast_to_role(
        message={
            "type": "new_session",
            "conversation_id": conversation_id,
            "patient_id": patient_id,
            "chief_complaint": chief_complaint,
            "department": department,
            "timestamp": datetime.utcnow().isoformat()
        },
        role="doctor"
    )



# 导出
__all__ = [
    "router",
    "push_status_update",
    "push_to_doctor",
    "broadcast_new_session"
]
