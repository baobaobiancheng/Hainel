"""
用户模型
定义用户相关的数据库模型
"""
from sqlalchemy import Column, String, Boolean, Enum, DateTime, Text, JSON
from sqlalchemy.orm import relationship

from app.models.base import BaseModel
from app.core.permissions import Role


class User(BaseModel):
    """用户模型"""
    
    __tablename__ = "users"
    
    # 基本信息
    username = Column(String(50), unique=True, nullable=False, index=True, comment="用户名")
    email = Column(String(100), unique=True, nullable=True, index=True, comment="邮箱")
    phone = Column(String(20), unique=True, nullable=True, index=True, comment="手机号")
    
    # 密码（存储哈希值）
    hashed_password = Column(String(255), nullable=False, comment="密码哈希值")
    
    # 角色
    role = Column(
        Enum(Role, values_callable=lambda x: [e.value for e in x]),
        default=Role.PATIENT,
        nullable=False,
        index=True,
        comment="用户角色：patient/doctor/admin",
    )
    
    # 个人信息
    full_name = Column(String(100), nullable=True, comment="全名")
    avatar_url = Column(String(500), nullable=True, comment="头像URL")
    bio = Column(Text, nullable=True, comment="个人简介")
    health_profile = Column(JSON, nullable=True, comment="患者健康档案")
    
    # 医生专用字段
    doctor_title = Column(String(50), nullable=True, comment="医生职称")
    doctor_department = Column(String(100), nullable=True, comment="医生科室")
    doctor_hospital = Column(String(200), nullable=True, comment="所属医院")
    doctor_license = Column(String(100), nullable=True, comment="执业证书编号")
    
    # 状态
    is_active = Column(Boolean, default=True, nullable=False, comment="是否激活")
    is_verified = Column(Boolean, default=False, nullable=False, comment="是否已验证")
    
    # 时间戳
    last_login_at = Column(DateTime, nullable=True, comment="最后登录时间")
    
    # 关系
    # 患者发起的会话
    patient_conversations = relationship(
        "Conversation",
        foreign_keys="Conversation.patient_id",
        back_populates="patient",
        cascade="all, delete-orphan",
    )
    
    # 医生参与的会话
    doctor_conversations = relationship(
        "Conversation",
        foreign_keys="Conversation.doctor_id",
        back_populates="doctor",
    )
    
    # 用户发送的消息
    messages = relationship(
        "Message",
        foreign_keys="Message.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    
    # 用户上传的病历
    medical_records = relationship(
        "MedicalRecord",
        foreign_keys="MedicalRecord.patient_id",
        back_populates="patient",
        cascade="all, delete-orphan",
    )
    
    # 医生审核的病历
    reviewed_records = relationship(
        "MedicalRecord",
        foreign_keys="MedicalRecord.reviewed_by",
        back_populates="reviewer",
    )
    
    def __repr__(self) -> str:
        """返回用户的字符串表示"""
        return f"<User(id={self.id}, username={self.username}, role={self.role.value})>"
    
    def to_dict(self, exclude: list = None) -> dict:
        """转换为字典，排除敏感信息"""
        exclude = exclude or []
        exclude.extend(['hashed_password'])
        return super().to_dict(exclude=exclude)


# 导出
__all__ = ["User"]

