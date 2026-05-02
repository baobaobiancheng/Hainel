"""
认证相关API
提供用户登录、注册、登出等功能
"""
from datetime import datetime, time
from mimetypes import guess_type
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.services.user_service import UserService
from app.schemas.user import (
    UserCreate,
    UserLogin,
    UserLoginResponse,
    UserResponse,
    UserUpdate,
    UserPasswordChange,
)
from app.core.security import security
from app.core.permissions import get_current_user
from app.models.conversation import Conversation
from app.models.medical_record import MedicalRecord
from app.models.message import Message
from app.models.reminder import Reminder
from app.models.enums import ReminderStatus
from app.utils.file_handler import file_handler, FileHandlerError
from app.core.exceptions import (
    AuthenticationException,
    NotFoundException,
    ConflictException,
    to_http_exception,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db),
):
    """
    用户注册
    
    Args:
        user_data: 用户注册数据
        db: 数据库会话
    
    Returns:
        创建的用户信息
    
    Raises:
        409: 用户名、邮箱或手机号已存在
    """
    try:
        user = UserService.create_user(user_data, db)
        return UserResponse.model_validate(user)
    except ConflictException as e:
        raise to_http_exception(e)
    except Exception as e:
        logger.error(f"用户注册失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="注册失败，请稍后重试"
        )


@router.post("/login", response_model=UserLoginResponse)
async def login(
    login_data: UserLogin,
    db: Session = Depends(get_db),
):
    """
    用户登录
    
    Args:
        login_data: 登录数据（用户名/邮箱/手机号 + 密码）
        db: 数据库会话
    
    Returns:
        访问令牌和用户信息
    
    Raises:
        401: 用户名或密码错误
    """
    try:
        user = UserService.authenticate_user(login_data, db)
        
        # 创建访问令牌
        access_token = security.create_access_token(
            data={
                "sub": str(user.id),
                "user_id": user.id,
                "username": user.username,
                "role": user.role.value,
            }
        )
        
        return UserLoginResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse.model_validate(user),
        )
    except AuthenticationException as e:
        raise to_http_exception(e)
    except Exception as e:
        logger.error(f"用户登录失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录失败，请稍后重试"
        )


@router.post("/logout")
async def logout(
    current_user: dict = Depends(get_current_user),
):
    """
    用户登出
    
    注意：由于使用JWT无状态认证，实际登出需要在客户端删除token
    这里主要用于记录登出日志
    
    Args:
        current_user: 当前用户信息
    
    Returns:
        登出成功消息
    """
    logger.info(f"用户登出: {current_user.get('username')} (ID: {current_user.get('id')})")
    return {"message": "登出成功"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取当前用户信息
    
    Args:
        current_user: 当前用户信息（从token解析）
        db: 数据库会话
    
    Returns:
        用户详细信息
    
    Raises:
        404: 用户不存在
    """
    try:
        user_id = current_user.get("id")
        user = UserService.get_user_by_id(user_id, db)
        if not user:
            raise NotFoundException(f"用户 ID {user_id} 不存在")
        return UserResponse.model_validate(user)
    except NotFoundException as e:
        raise to_http_exception(e)
    except Exception as e:
        logger.error(f"获取用户信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户信息失败"
        )


@router.get("/me/stats")
async def get_current_user_stats(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前患者端首页所需的实时统计数据。"""
    user_id = current_user.get("id")
    today = datetime.now().date()
    today_start = datetime.combine(today, time.min)
    today_end = datetime.combine(today, time.max)

    conversation_count = (
        db.query(Conversation)
        .filter(Conversation.patient_id == user_id)
        .count()
    )
    medical_record_count = (
        db.query(MedicalRecord)
        .filter(MedicalRecord.patient_id == user_id)
        .count()
    )
    uploaded_report_count = (
        db.query(Message)
        .filter(Message.user_id == user_id, Message.file_url.isnot(None))
        .count()
    )
    today_reminder_count = (
        db.query(Reminder)
        .filter(
            Reminder.user_id == user_id,
            Reminder.status.in_([ReminderStatus.ACTIVE, ReminderStatus.COMPLETED]),
            (Reminder.start_date.is_(None)) | (Reminder.start_date <= today_end),
            (Reminder.end_date.is_(None)) | (Reminder.end_date >= today_start),
        )
        .count()
    )

    return {
        "conversation_count": conversation_count,
        "today_reminder_count": today_reminder_count,
        "report_count": uploaded_report_count or medical_record_count,
    }


@router.post("/me/avatar", response_model=UserResponse)
async def upload_current_user_avatar(
    file: UploadFile = File(..., description="头像图片文件"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """上传并更新当前用户头像。"""
    user_id = current_user.get("id")
    user = UserService.get_user_by_id(user_id, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in {"jpg", "jpeg", "png", "webp", "bmp"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="头像仅支持 jpg、jpeg、png、webp、bmp 格式",
        )

    try:
        filename = await file_handler.save_upload_file(file, subdir=f"avatars/{user_id}")
    except FileHandlerError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"头像上传失败: {e}",
        )

    user.avatar_url = f"/auth/avatars/{user_id}/{filename}"
    db.commit()
    db.refresh(user)
    logger.info(f"用户 {user_id} 更新头像: {filename}")
    return UserResponse.model_validate(user)


@router.get("/avatars/{user_id}/{filename}")
async def get_avatar_file(user_id: int, filename: str):
    """读取头像图片。头像用于前端展示，不要求额外认证头。"""
    try:
        content = await file_handler.read_file(filename, subdir=f"avatars/{user_id}")
    except FileHandlerError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"头像不存在: {e}")

    media_type = guess_type(filename)[0] or "application/octet-stream"
    return Response(content=content, media_type=media_type)


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    更新当前用户信息
    
    Args:
        user_data: 用户更新数据
        current_user: 当前用户信息
        db: 数据库会话
    
    Returns:
        更新后的用户信息
    
    Raises:
        404: 用户不存在
        409: 邮箱或手机号已被其他用户使用
    """
    try:
        user_id = current_user.get("id")
        user = UserService.update_user(user_id, user_data, db)
        return UserResponse.model_validate(user)
    except NotFoundException as e:
        raise to_http_exception(e)
    except ConflictException as e:
        raise to_http_exception(e)
    except Exception as e:
        logger.error(f"更新用户信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新用户信息失败"
        )


@router.post("/change-password")
async def change_password(
    password_data: UserPasswordChange,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    修改密码
    
    Args:
        password_data: 密码修改数据（旧密码 + 新密码）
        current_user: 当前用户信息
        db: 数据库会话
    
    Returns:
        修改成功消息
    
    Raises:
        401: 旧密码错误
        404: 用户不存在
    """
    try:
        user_id = current_user.get("id")
        UserService.change_password(
            user_id,
            password_data.old_password,
            password_data.new_password,
            db,
        )
        return {"message": "密码修改成功"}
    except AuthenticationException as e:
        raise to_http_exception(e)
    except NotFoundException as e:
        raise to_http_exception(e)
    except Exception as e:
        logger.error(f"修改密码失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="修改密码失败"
        )


# 导出
__all__ = ["router"]

