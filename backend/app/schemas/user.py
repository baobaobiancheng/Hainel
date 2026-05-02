"""
用户相关的 Pydantic 模式
定义用户相关的请求和响应验证模式
"""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserBase(BaseModel):
    """用户基础模式"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    full_name: Optional[str] = Field(None, max_length=100, description="全名")
    avatar_url: Optional[str] = Field(None, max_length=500, description="头像URL")
    bio: Optional[str] = Field(None, description="个人简介")


class UserCreate(UserBase):
    """创建用户请求模式"""
    password: str = Field(..., min_length=6, max_length=100, description="密码")
    role: Optional[str] = Field("patient", description="用户角色：patient/doctor/admin")
    health_profile: Optional[Dict[str, Any]] = Field(None, description="患者健康档案")


class UserUpdate(BaseModel):
    """更新用户请求模式（所有字段可选）"""
    email: Optional[EmailStr] = Field(None, description="邮箱")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    full_name: Optional[str] = Field(None, max_length=100, description="全名")
    avatar_url: Optional[str] = Field(None, max_length=500, description="头像URL")
    bio: Optional[str] = Field(None, description="个人简介")
    health_profile: Optional[Dict[str, Any]] = Field(None, description="患者健康档案")
    password: Optional[str] = Field(None, min_length=6, max_length=100, description="新密码")


class DoctorInfoUpdate(BaseModel):
    """医生信息更新模式"""
    doctor_title: Optional[str] = Field(None, max_length=50, description="医生职称")
    doctor_department: Optional[str] = Field(None, max_length=100, description="医生科室")
    doctor_hospital: Optional[str] = Field(None, max_length=200, description="所属医院")
    doctor_license: Optional[str] = Field(None, max_length=100, description="执业证书编号")


class UserResponse(UserBase):
    """用户响应模式"""
    id: int = Field(..., description="用户ID")
    role: str = Field(..., description="用户角色")
    doctor_title: Optional[str] = Field(None, description="医生职称")
    doctor_department: Optional[str] = Field(None, description="医生科室")
    doctor_hospital: Optional[str] = Field(None, description="所属医院")
    doctor_license: Optional[str] = Field(None, description="执业证书编号")
    health_profile: Optional[Dict[str, Any]] = Field(None, description="患者健康档案")
    is_active: bool = Field(..., description="是否激活")
    is_verified: bool = Field(..., description="是否已验证")
    last_login_at: Optional[datetime] = Field(None, description="最后登录时间")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    model_config = ConfigDict(from_attributes=True)


class UserPublic(UserBase):
    """用户公开信息模式（不包含敏感信息）"""
    id: int = Field(..., description="用户ID")
    role: str = Field(..., description="用户角色")
    doctor_title: Optional[str] = Field(None, description="医生职称")
    doctor_department: Optional[str] = Field(None, description="医生科室")
    doctor_hospital: Optional[str] = Field(None, description="所属医院")
    is_active: bool = Field(..., description="是否激活")
    created_at: datetime = Field(..., description="创建时间")
    
    model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
    """用户登录请求模式"""
    username: str = Field(..., description="用户名或邮箱或手机号")
    password: str = Field(..., description="密码")


class UserLoginResponse(BaseModel):
    """用户登录响应模式"""
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    user: UserResponse = Field(..., description="用户信息")


class UserPasswordChange(BaseModel):
    """修改密码请求模式"""
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=6, max_length=100, description="新密码")


class UserPasswordReset(BaseModel):
    """重置密码请求模式"""
    email: EmailStr = Field(..., description="邮箱")
    reset_code: str = Field(..., description="重置验证码")
    new_password: str = Field(..., min_length=6, max_length=100, description="新密码")


# 导出
__all__ = [
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "DoctorInfoUpdate",
    "UserResponse",
    "UserPublic",
    "UserLogin",
    "UserLoginResponse",
    "UserPasswordChange",
    "UserPasswordReset",
]

