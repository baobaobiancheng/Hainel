"""
用户相关 Schema
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from app.models.user import UserRole


class UserBase(BaseModel):
    """用户基础模型"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr


class UserCreate(UserBase):
    """用户注册模型"""
    password: str = Field(..., min_length=6, max_length=50)


class UserLogin(BaseModel):
    """用户登录模型"""
    username_or_email: str
    password: str


class UserUpdate(BaseModel):
    """用户更新模型"""
    nickname: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None


class UserResponse(UserBase):
    """用户响应模型"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    nickname: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None


class TokenResponse(BaseModel):
    """Token 响应模型"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    """Token 负载模型"""
    sub: str  # user_id
    exp: int
    type: str

