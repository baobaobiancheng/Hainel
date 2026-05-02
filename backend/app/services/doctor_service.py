"""
医生服务
提供医生相关的业务逻辑处理，包括医生分配
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from enum import Enum

from app.models.user import User
from app.models.conversation import Conversation, ConversationStatus
from app.core.permissions import Role
from app.utils.logger import get_logger


class Department(Enum):
    """科室枚举"""
    INTERNAL = "internal"          # 内科
    SURGERY = "surgery"            # 外科
    PEDIATRICS = "pediatrics"      # 儿科
    GYNECOLOGY = "gynecology"       # 妇科
    CARDIOLOGY = "cardiology"      # 心内科
    NEUROLOGY = "neurology"        # 神经内科
    ORTHOPEDICS = "orthopedics"    # 骨科
    DERMATOLOGY = "dermatology"    # 皮肤科
    OPHTHALMOLOGY = "ophthalmology"  # 眼科
    ENT = "ent"                    # 耳鼻喉科
    PSYCHIATRY = "psychiatry"      # 精神科
    EMERGENCY = "emergency"        # 急诊科
    GENERAL = "general"            # 全科


DEPARTMENT_CHINESE = {
    Department.INTERNAL: "内科",
    Department.SURGERY: "外科",
    Department.PEDIATRICS: "儿科",
    Department.GYNECOLOGY: "妇科",
    Department.CARDIOLOGY: "心内科",
    Department.NEUROLOGY: "神经内科",
    Department.ORTHOPEDICS: "骨科",
    Department.DERMATOLOGY: "皮肤科",
    Department.OPHTHALMOLOGY: "眼科",
    Department.ENT: "耳鼻喉科",
    Department.PSYCHIATRY: "精神科",
    Department.EMERGENCY: "急诊科",
    Department.GENERAL: "全科",
}

STANDARD_DOCTOR_IDS = tuple(range(5, 18))

logger = get_logger(__name__)


class DoctorService:
    """医生服务类"""

    @staticmethod
    def get_doctor_by_id(doctor_id: int, db: Session) -> Optional[User]:
        """
        根据ID获取医生

        Args:
            doctor_id: 医生ID
            db: 数据库会话

        Returns:
            医生用户对象，如果不存在返回None
        """
        return db.query(User).filter(
            and_(
                User.id == doctor_id,
                User.role == Role.DOCTOR,
                User.is_active == True,
            )
        ).first()

    @staticmethod
    def get_doctors_by_department(
        department: Department,
        db: Session,
        active_only: bool = True,
    ) -> List[User]:
        """
        获取指定科室的医生列表

        Args:
            department: 科室
            db: 数据库会话
            active_only: 是否只返回活跃的医生

        Returns:
            医生用户列表
        """
        query = db.query(User).filter(
            User.role == Role.DOCTOR,
            User.id.in_(STANDARD_DOCTOR_IDS),
        )

        # 匹配科室（模糊匹配）
        department_name = DEPARTMENT_CHINESE.get(department, "")
        query = query.filter(User.doctor_department.contains(department_name))

        if active_only:
            query = query.filter(User.is_active == True)

        return query.order_by(User.id).all()

    @staticmethod
    def find_available_doctor(
        department: Department,
        db: Session,
    ) -> Optional[User]:
        """
        为指定科室寻找可用的医生（当前没有活跃会话的医生）

        Args:
            department: 科室
            db: 数据库会话

        Returns:
            可用的医生用户对象，如果不存在返回None
        """
        # 获取该科室的所有活跃医生
        doctors = DoctorService.get_doctors_by_department(department, db, active_only=True)

        if not doctors:
            logger.warning(f"没有找到科室 {DEPARTMENT_CHINESE.get(department, department.value)} 的医生")
            return None

        active_statuses = [ConversationStatus.ACTIVE, ConversationStatus.PENDING]
        doctor_ids = [doctor.id for doctor in doctors]
        active_counts = {
            doctor_id: count
            for doctor_id, count in (
                db.query(Conversation.doctor_id, func.count(Conversation.id))
                .filter(
                    Conversation.doctor_id.in_(doctor_ids),
                    Conversation.status.in_(active_statuses),
                )
                .group_by(Conversation.doctor_id)
                .all()
            )
        }

        selected_doctor = min(
            doctors,
            key=lambda doctor: (active_counts.get(doctor.id, 0), doctor.id),
        )
        selected_count = active_counts.get(selected_doctor.id, 0)

        if selected_count == 0:
            logger.info(f"找到可用医生: {selected_doctor.username} (ID: {selected_doctor.id})")
        else:
            logger.info(
                f"所有 {DEPARTMENT_CHINESE.get(department, department.value)} 科室医生都有活跃会话，"
                f"选择当前活跃会话最少的医生: {selected_doctor.username} "
                f"(ID: {selected_doctor.id}, active_count={selected_count})"
            )
        return selected_doctor

    @staticmethod
    def assign_doctor_to_conversation(
        conversation_id: int,
        doctor_id: int,
        db: Session,
    ) -> bool:
        """
        为会话分配医生

        Args:
            conversation_id: 会话ID
            doctor_id: 医生ID
            db: 数据库会话

        Returns:
            是否分配成功
        """
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            logger.error(f"会话 {conversation_id} 不存在")
            return False

        doctor = DoctorService.get_doctor_by_id(doctor_id, db)
        if not doctor:
            logger.error(f"医生 {doctor_id} 不存在")
            return False

        conversation.doctor_id = doctor_id
        db.commit()

        logger.info(f"成功为会话 {conversation_id} 分配医生 {doctor.username} (ID: {doctor_id})")
        return True

    @staticmethod
    def auto_assign_doctor(
        conversation_id: int,
        department: Department,
        db: Session,
    ) -> Optional[User]:
        """
        自动为会话分配医生

        Args:
            conversation_id: 会话ID
            department: 科室
            db: 数据库会话

        Returns:
            分配的医生用户对象，如果分配失败返回None
        """
        # 寻找可用医生
        doctor = DoctorService.find_available_doctor(department, db)

        if not doctor:
            logger.warning(f"无法为会话 {conversation_id} 分配医生（科室：{department.value}）")
            return None

        # 分配医生
        success = DoctorService.assign_doctor_to_conversation(
            conversation_id, doctor.id, db
        )

        if success:
            return doctor
        return None

    @staticmethod
    def get_all_doctors(
        db: Session,
        include_inactive: bool = False,
    ) -> List[User]:
        """
        获取所有医生

        Args:
            db: 数据库会话
            include_inactive: 是否包含未激活的医生

        Returns:
            医生用户列表
        """
        query = db.query(User).filter(User.role == Role.DOCTOR)

        if not include_inactive:
            query = query.filter(User.is_active == True)

        return query.all()

    @staticmethod
    def get_doctor_stats(doctor_id: int, db: Session) -> dict:
        """
        获取医生的统计数据

        Args:
            doctor_id: 医生ID
            db: 数据库会话

        Returns:
            统计数据字典
        """
        doctor = DoctorService.get_doctor_by_id(doctor_id, db)
        if not doctor:
            return {}

        # 统计会话数量
        total_conversations = db.query(Conversation).filter(
            Conversation.doctor_id == doctor_id
        ).count()

        active_conversations = db.query(Conversation).filter(
            and_(
                Conversation.doctor_id == doctor_id,
                Conversation.status.in_([ConversationStatus.ACTIVE, ConversationStatus.PENDING]),
            )
        ).count()

        completed_conversations = db.query(Conversation).filter(
            and_(
                Conversation.doctor_id == doctor_id,
                Conversation.status == ConversationStatus.COMPLETED,
            )
        ).count()

        return {
            "doctor_id": doctor_id,
            "doctor_name": doctor.username,
            "department": doctor.doctor_department,
            "total_conversations": total_conversations,
            "active_conversations": active_conversations,
            "completed_conversations": completed_conversations,
        }


# 创建全局服务实例
doctor_service = DoctorService()


# 导出
__all__ = ["DoctorService", "doctor_service", "STANDARD_DOCTOR_IDS"]
