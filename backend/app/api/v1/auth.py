"""
认证相关API
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.exceptions import AuthenticationError, AlreadyExists
from app.config import settings
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserResponse, TokenResponse
from app.schemas.common import ResponseModel

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """获取当前用户（依赖注入）"""
    payload = decode_token(token)
    if not payload:
        raise AuthenticationError("无效的 Token")
    
    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError("Token 中缺少用户信息")
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise AuthenticationError("用户不存在")
    
    if not user.is_active:
        raise AuthenticationError("用户已被禁用")
    
    return user


@router.post("/register", response_model=ResponseModel[UserResponse])
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """用户注册"""
    # 检查用户名是否存在
    result = await db.execute(
        select(User).where(User.username == user_data.username)
    )
    if result.scalar_one_or_none():
        raise AlreadyExists("用户名已存在")
    
    # 检查邮箱是否存在
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    if result.scalar_one_or_none():
        raise AlreadyExists("邮箱已被注册")
    
    # 创建用户
    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return ResponseModel(
        success=True,
        message="注册成功",
        data=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=ResponseModel[TokenResponse])
async def login(
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """用户登录"""
    # 查找用户（支持用户名或邮箱）
    result = await db.execute(
        select(User).where(
            (User.username == login_data.username_or_email) |
            (User.email == login_data.username_or_email)
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise AuthenticationError("用户名或密码错误")
    
    # 验证密码
    if not verify_password(login_data.password, user.password_hash):
        raise AuthenticationError("用户名或密码错误")
    
    if not user.is_active:
        raise AuthenticationError("用户已被禁用")
    
    # 生成 Token
    token_data = {"sub": str(user.id), "email": user.email}
    
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return ResponseModel(
        success=True,
        message="登录成功",
        data=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        ),
    )


@router.get("/me", response_model=ResponseModel[UserResponse])
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """获取当前用户信息"""
    return ResponseModel(
        success=True,
        message="获取成功",
        data=UserResponse.model_validate(current_user),
    )


@router.post("/refresh", response_model=ResponseModel[TokenResponse])
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db),
):
    """刷新 Token"""
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise AuthenticationError("无效的 Refresh Token")
    
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise AuthenticationError("用户不存在或已被禁用")
    
    # 生成新的 Token
    token_data = {"sub": str(user.id), "email": user.email}
    new_access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)
    
    return ResponseModel(
        success=True,
        message="Token 刷新成功",
        data=TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        ),
    )

