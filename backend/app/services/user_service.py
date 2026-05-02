"""
用户服务
提供用户相关的业务逻辑处理
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.models.user import User
from app.models.conversation import Conversation
from app.models.medical_record import MedicalRecord
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    DoctorInfoUpdate,
    UserLogin,
)
from app.core.security import security
from app.core.permissions import Role
from app.core.exceptions import (
    NotFoundException,
    ConflictException,
    AuthenticationException,
    BusinessException,
)
from app.database.session import get_session
from app.utils.logger import get_logger

logger = get_logger(__name__)


class UserService:
    """用户服务类"""
    
    @staticmethod
    def create_user(user_data: UserCreate, db: Session) -> User:
        """
        创建新用户
        
        Args:
            user_data: 用户创建数据
            db: 数据库会话
        
        Returns:
            创建的用户对象
        
        Raises:
            ConflictException: 用户名、邮箱或手机号已存在
        """
        # 检查用户名是否已存在
        existing_user = db.query(User).filter(User.username == user_data.username).first()
        if existing_user:
            raise ConflictException(f"用户名 '{user_data.username}' 已存在")
        
        # 检查邮箱是否已存在
        if user_data.email:
            existing_email = db.query(User).filter(User.email == user_data.email).first()
            if existing_email:
                raise ConflictException(f"邮箱 '{user_data.email}' 已存在")
        
        # 检查手机号是否已存在
        if user_data.phone:
            existing_phone = db.query(User).filter(User.phone == user_data.phone).first()
            if existing_phone:
                raise ConflictException(f"手机号 '{user_data.phone}' 已存在")
        
        # 创建用户对象
        user = User(
            username=user_data.username,
            email=user_data.email,
            phone=user_data.phone,
            full_name=user_data.full_name,
            avatar_url=user_data.avatar_url,
            bio=user_data.bio,
            health_profile=user_data.health_profile,
            hashed_password=security.get_password_hash(user_data.password),
            role=Role(user_data.role) if user_data.role else Role.PATIENT,
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        logger.info(f"创建用户成功: {user.username} (ID: {user.id})")
        return user
    
    @staticmethod
    def get_user_by_id(user_id: int, db: Session) -> Optional[User]:
        """
        根据ID获取用户
        
        Args:
            user_id: 用户ID
            db: 数据库会话
        
        Returns:
            用户对象，如果不存在返回None
        """
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def get_user_by_username(username: str, db: Session) -> Optional[User]:
        """
        根据用户名获取用户
        
        Args:
            username: 用户名
            db: 数据库会话
        
        Returns:
            用户对象，如果不存在返回None
        """
        return db.query(User).filter(User.username == username).first()
    
    @staticmethod
    def get_user_by_email(email: str, db: Session) -> Optional[User]:
        """
        根据邮箱获取用户
        
        Args:
            email: 邮箱
            db: 数据库会话
        
        Returns:
            用户对象，如果不存在返回None
        """
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def get_user_by_phone(phone: str, db: Session) -> Optional[User]:
        """
        根据手机号获取用户
        
        Args:
            phone: 手机号
            db: 数据库会话
        
        Returns:
            用户对象，如果不存在返回None
        """
        return db.query(User).filter(User.phone == phone).first()
    
    @staticmethod
    def authenticate_user(login_data: UserLogin, db: Session) -> User:
        """
        用户认证（登录）
        
        Args:
            login_data: 登录数据（用户名/邮箱/手机号 + 密码）
            db: 数据库会话
        
        Returns:
            认证成功的用户对象
        
        Raises:
            AuthenticationException: 认证失败
        """
        # 尝试通过用户名、邮箱或手机号查找用户
        user = (
            db.query(User)
            .filter(
                or_(
                    User.username == login_data.username,
                    User.email == login_data.username,
                    User.phone == login_data.username,
                )
            )
            .first()
        )
        
        if not user:
            raise AuthenticationException("用户名或密码错误")
        
        if not user.is_active:
            raise AuthenticationException("用户账号已被禁用")
        
        # 验证密码
        if not security.verify_password(login_data.password, user.hashed_password):
            raise AuthenticationException("用户名或密码错误")
        
        # 更新最后登录时间
        user.last_login_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"用户登录成功: {user.username} (ID: {user.id})")
        return user
    
    @staticmethod
    def update_user(user_id: int, user_data: UserUpdate, db: Session) -> User:
        """
        更新用户信息
        
        Args:
            user_id: 用户ID
            user_data: 用户更新数据
            db: 数据库会话
        
        Returns:
            更新后的用户对象
        
        Raises:
            NotFoundException: 用户不存在
            ConflictException: 邮箱或手机号已被其他用户使用
        """
        user = UserService.get_user_by_id(user_id, db)
        if not user:
            raise NotFoundException(f"用户 ID {user_id} 不存在")
        
        # 检查邮箱是否被其他用户使用
        if user_data.email and user_data.email != user.email:
            existing_email = db.query(User).filter(
                and_(User.email == user_data.email, User.id != user_id)
            ).first()
            if existing_email:
                raise ConflictException(f"邮箱 '{user_data.email}' 已被其他用户使用")
        
        # 检查手机号是否被其他用户使用
        if user_data.phone and user_data.phone != user.phone:
            existing_phone = db.query(User).filter(
                and_(User.phone == user_data.phone, User.id != user_id)
            ).first()
            if existing_phone:
                raise ConflictException(f"手机号 '{user_data.phone}' 已被其他用户使用")
        
        # 更新字段
        update_dict = user_data.model_dump(exclude_unset=True)
        
        # 如果更新密码，需要加密
        if "password" in update_dict:
            update_dict["hashed_password"] = security.get_password_hash(update_dict.pop("password"))
        
        user.update_from_dict(update_dict)
        db.commit()
        db.refresh(user)
        
        logger.info(f"更新用户成功: {user.username} (ID: {user.id})")
        return user
    
    @staticmethod
    def update_doctor_info(user_id: int, doctor_data: DoctorInfoUpdate, db: Session) -> User:
        """
        更新医生信息
        
        Args:
            user_id: 用户ID
            doctor_data: 医生信息更新数据
            db: 数据库会话
        
        Returns:
            更新后的用户对象
        
        Raises:
            NotFoundException: 用户不存在
            BusinessException: 用户不是医生角色
        """
        user = UserService.get_user_by_id(user_id, db)
        if not user:
            raise NotFoundException(f"用户 ID {user_id} 不存在")
        
        if user.role != Role.DOCTOR:
            raise BusinessException("只有医生角色才能更新医生信息")
        
        update_dict = doctor_data.model_dump(exclude_unset=True)
        user.update_from_dict(update_dict)
        db.commit()
        db.refresh(user)
        
        logger.info(f"更新医生信息成功: {user.username} (ID: {user.id})")
        return user
    
    @staticmethod
    def change_password(user_id: int, old_password: str, new_password: str, db: Session) -> User:
        """
        修改密码
        
        Args:
            user_id: 用户ID
            old_password: 旧密码
            new_password: 新密码
            db: 数据库会话
        
        Returns:
            更新后的用户对象
        
        Raises:
            NotFoundException: 用户不存在
            AuthenticationException: 旧密码错误
        """
        user = UserService.get_user_by_id(user_id, db)
        if not user:
            raise NotFoundException(f"用户 ID {user_id} 不存在")
        
        # 验证旧密码
        if not security.verify_password(old_password, user.hashed_password):
            raise AuthenticationException("旧密码错误")
        
        # 更新密码
        user.hashed_password = security.get_password_hash(new_password)
        db.commit()
        db.refresh(user)
        
        logger.info(f"修改密码成功: {user.username} (ID: {user.id})")
        return user
    
    @staticmethod
    def delete_user(user_id: int, db: Session) -> bool:
        """
        删除用户（软删除：设置为非激活状态）
        
        Args:
            user_id: 用户ID
            db: 数据库会话
        
        Returns:
            是否删除成功
        
        Raises:
            NotFoundException: 用户不存在
        """
        user = UserService.get_user_by_id(user_id, db)
        if not user:
            raise NotFoundException(f"用户 ID {user_id} 不存在")
        
        # 软删除：设置为非激活状态
        user.is_active = False
        db.commit()
        
        logger.info(f"删除用户成功: {user.username} (ID: {user.id})")
        return True
    
    @staticmethod
    def list_users(
        skip: int = 0,
        limit: int = 100,
        role: Optional[Role] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        db: Session = None,
    ) -> tuple[List[User], int]:
        """
        获取用户列表
        
        Args:
            skip: 跳过的记录数
            limit: 返回的记录数
            role: 角色过滤
            is_active: 是否激活过滤
            search: 搜索关键词（用户名、邮箱、手机号）
            db: 数据库会话
        
        Returns:
            (用户列表, 总数量)
        """
        if db is None:
            with get_session() as session:
                return UserService.list_users(skip, limit, role, is_active, search, session)
        
        query = db.query(User)
        
        # 角色过滤
        if role:
            query = query.filter(User.role == role)
        
        # 激活状态过滤
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        
        # 搜索过滤
        if search:
            search_filter = or_(
                User.username.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.phone.ilike(f"%{search}%"),
                User.full_name.ilike(f"%{search}%"),
            )
            query = query.filter(search_filter)
        
        # 获取总数
        total = query.count()
        
        # 分页
        users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
        
        return users, total
    
    @staticmethod
    def get_user_statistics(user_id: int, db: Session) -> Dict[str, Any]:
        """
        获取用户统计信息
        
        Args:
            user_id: 用户ID
            db: 数据库会话
        
        Returns:
            统计信息字典
        
        Raises:
            NotFoundException: 用户不存在
        """
        user = UserService.get_user_by_id(user_id, db)
        if not user:
            raise NotFoundException(f"用户 ID {user_id} 不存在")
        
        stats = {
            "user_id": user_id,
            "conversation_count": 0,
            "message_count": 0,
            "medical_record_count": 0,
        }
        
        if user.role == Role.PATIENT:
            # 患者统计
            stats["conversation_count"] = (
                db.query(Conversation)
                .filter(Conversation.patient_id == user_id)
                .count()
            )
            stats["medical_record_count"] = (
                db.query(MedicalRecord)
                .filter(MedicalRecord.patient_id == user_id)
                .count()
            )
        elif user.role == Role.DOCTOR:
            # 医生统计
            stats["conversation_count"] = (
                db.query(Conversation)
                .filter(Conversation.doctor_id == user_id)
                .count()
            )
            stats["medical_record_count"] = (
                db.query(MedicalRecord)
                .filter(MedicalRecord.reviewed_by == user_id)
                .count()
            )
        
        return stats
    


# 创建全局服务实例
user_service = UserService()


# 导出
__all__ = ["UserService", "user_service"]

