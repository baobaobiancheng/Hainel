"""
病历服务
提供病历相关的业务逻辑处理
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from app.models.medical_record import MedicalRecord, MedicalRecordStatus
from app.models.user import User
from app.models.conversation import Conversation
from app.schemas.medical_record import (
    MedicalRecordCreate,
    MedicalRecordUpdate,
    MedicalRecordStatusUpdate,
    MedicalRecordReview,
)
from app.core.exceptions import (
    NotFoundException,
    ValidationException,
    BusinessException,
    AuthorizationException,
)
from app.core.permissions import Role
from app.database.session import get_session
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MedicalRecordService:
    """病历服务类"""
    
    @staticmethod
    def create_medical_record(
        record_data: MedicalRecordCreate,
        db: Session,
    ) -> MedicalRecord:
        """
        创建新病历
        
        Args:
            record_data: 病历创建数据
            db: 数据库会话
        
        Returns:
            创建的病历对象
        
        Raises:
            NotFoundException: 患者或会话不存在
        """
        # 验证患者是否存在
        patient = db.query(User).filter(User.id == record_data.patient_id).first()
        if not patient:
            raise NotFoundException(f"患者 ID {record_data.patient_id} 不存在")
        
        # 验证会话是否存在（如果指定了会话）
        if record_data.conversation_id:
            conversation = db.query(Conversation).filter(
                Conversation.id == record_data.conversation_id
            ).first()
            if not conversation:
                raise NotFoundException(f"会话 ID {record_data.conversation_id} 不存在")
        
        # 创建病历对象
        medical_record = MedicalRecord(
            patient_id=record_data.patient_id,
            conversation_id=record_data.conversation_id,
            title=record_data.title,
            chief_complaint=record_data.chief_complaint,
            present_illness=record_data.present_illness,
            past_history=record_data.past_history,
            physical_examination=record_data.physical_examination,
            auxiliary_examination=record_data.auxiliary_examination,
            diagnosis=record_data.diagnosis,
            treatment_plan=record_data.treatment_plan,
            medications=record_data.medications,
            medical_advice=record_data.medical_advice,
            follow_up=record_data.follow_up,
            content=record_data.content,
            agent_name=record_data.agent_name,
            agent_id=record_data.agent_id,
            extra_metadata=record_data.metadata,
            status=MedicalRecordStatus.DRAFT,
        )
        
        db.add(medical_record)
        db.commit()
        db.refresh(medical_record)
        
        logger.info(f"创建病历成功: ID {medical_record.id}, 患者 ID {medical_record.patient_id}")
        return medical_record
    
    @staticmethod
    def get_medical_record_by_id(record_id: int, db: Session) -> Optional[MedicalRecord]:
        """
        根据ID获取病历
        
        Args:
            record_id: 病历ID
            db: 数据库会话
        
        Returns:
            病历对象，如果不存在返回None
        """
        return db.query(MedicalRecord).filter(MedicalRecord.id == record_id).first()
    
    @staticmethod
    def update_medical_record(
        record_id: int,
        record_data: MedicalRecordUpdate,
        db: Session,
    ) -> MedicalRecord:
        """
        更新病历信息
        
        Args:
            record_id: 病历ID
            record_data: 病历更新数据
            db: 数据库会话
        
        Returns:
            更新后的病历对象
        
        Raises:
            NotFoundException: 病历不存在
            BusinessException: 病历状态不允许编辑
        """
        medical_record = MedicalRecordService.get_medical_record_by_id(record_id, db)
        if not medical_record:
            raise NotFoundException(f"病历 ID {record_id} 不存在")
        
        # 检查病历状态，已审核或已归档的病历不允许编辑
        if medical_record.status in [MedicalRecordStatus.REVIEWED, MedicalRecordStatus.ARCHIVED]:
            raise BusinessException(f"病历状态为 {medical_record.status.value}，不允许编辑")
        
        # 更新字段
        update_dict = record_data.model_dump(exclude_unset=True)
        medical_record.update_from_dict(update_dict)
        
        # 如果更新了内容，状态改为已确认（如果之前是草稿）
        db.commit()
        db.refresh(medical_record)
        
        logger.info(f"更新病历成功: ID {medical_record.id}")
        return medical_record
    
    @staticmethod
    def update_medical_record_status(
        record_id: int,
        status_data: MedicalRecordStatusUpdate,
        db: Session,
    ) -> MedicalRecord:
        """
        更新病历状态
        
        Args:
            record_id: 病历ID
            status_data: 状态更新数据
            db: 数据库会话
        
        Returns:
            更新后的病历对象
        
        Raises:
            NotFoundException: 病历不存在
            ValidationException: 无效的状态值
        """
        medical_record = MedicalRecordService.get_medical_record_by_id(record_id, db)
        if not medical_record:
            raise NotFoundException(f"病历 ID {record_id} 不存在")
        
        try:
            new_status = MedicalRecordStatus(status_data.status)
        except ValueError:
            raise ValidationException(f"无效的病历状态: {status_data.status}")
        
        # 根据状态执行相应操作
        if new_status == MedicalRecordStatus.CONFIRMED:
            medical_record.mark_as_confirmed()
        elif new_status == MedicalRecordStatus.ARCHIVED:
            medical_record.mark_as_archived()
        else:
            medical_record.status = new_status
        
        db.commit()
        db.refresh(medical_record)
        
        logger.info(f"更新病历状态成功: ID {medical_record.id}, 状态: {new_status.value}")
        return medical_record
    
    @staticmethod
    def review_medical_record(
        record_id: int,
        reviewer_id: int,
        review_data: MedicalRecordReview,
        db: Session,
    ) -> MedicalRecord:
        """
        审核病历
        
        Args:
            record_id: 病历ID
            reviewer_id: 审核医生ID
            review_data: 审核数据
            db: 数据库会话
        
        Returns:
            更新后的病历对象
        
        Raises:
            NotFoundException: 病历或医生不存在
            BusinessException: 病历状态不允许审核
            AuthorizationException: 用户不是医生
        """
        medical_record = MedicalRecordService.get_medical_record_by_id(record_id, db)
        if not medical_record:
            raise NotFoundException(f"病历 ID {record_id} 不存在")
        
        # 验证审核医生是否存在且是医生角色
        reviewer = db.query(User).filter(User.id == reviewer_id).first()
        if not reviewer:
            raise NotFoundException(f"医生 ID {reviewer_id} 不存在")
        
        if reviewer.role not in (Role.DOCTOR, Role.ADMIN):
            raise AuthorizationException("只有医生或管理员才能审核病历")
        
        # 检查病历状态
        if medical_record.status == MedicalRecordStatus.ARCHIVED:
            raise BusinessException("已归档的病历不允许审核")
        
        # 执行审核
        if review_data.approve:
            medical_record.mark_as_reviewed(
                reviewer_id=reviewer_id,
                comment=review_data.review_comment,
            )
        else:
            # 如果不通过审核，可以设置为草稿状态，让医生重新编辑
            medical_record.status = MedicalRecordStatus.DRAFT
            medical_record.reviewed_by = reviewer_id
            medical_record.review_comment = review_data.review_comment
            medical_record.reviewed_at = datetime.utcnow()
        
        db.commit()
        db.refresh(medical_record)
        
        logger.info(
            f"审核病历成功: ID {medical_record.id}, "
            f"审核医生 ID {reviewer_id}, 结果: {'通过' if review_data.approve else '不通过'}"
        )
        return medical_record
    
    @staticmethod
    def archive_medical_record(record_id: int, db: Session) -> MedicalRecord:
        """
        归档病历
        
        Args:
            record_id: 病历ID
            db: 数据库会话
        
        Returns:
            更新后的病历对象
        
        Raises:
            NotFoundException: 病历不存在
            BusinessException: 病历状态不允许归档
        """
        medical_record = MedicalRecordService.get_medical_record_by_id(record_id, db)
        if not medical_record:
            raise NotFoundException(f"病历 ID {record_id} 不存在")
        
        # 只有已审核的病历才能归档
        if medical_record.status != MedicalRecordStatus.REVIEWED:
            raise BusinessException("只有已审核的病历才能归档")
        
        medical_record.mark_as_archived()
        db.commit()
        db.refresh(medical_record)
        
        logger.info(f"归档病历成功: ID {medical_record.id}")
        return medical_record
    
    @staticmethod
    def list_medical_records(
        skip: int = 0,
        limit: int = 100,
        patient_id: Optional[int] = None,
        conversation_id: Optional[int] = None,
        reviewed_by: Optional[int] = None,
        status: Optional[MedicalRecordStatus] = None,
        db: Session = None,
    ) -> tuple[List[MedicalRecord], int]:
        """
        获取病历列表
        
        Args:
            skip: 跳过的记录数
            limit: 返回的记录数
            patient_id: 患者ID过滤
            conversation_id: 会话ID过滤
            reviewed_by: 审核医生ID过滤
            status: 状态过滤
            db: 数据库会话
        
        Returns:
            (病历列表, 总数量)
        """
        if db is None:
            with get_session() as session:
                return MedicalRecordService.list_medical_records(
                    skip, limit, patient_id, conversation_id, reviewed_by, status, session
                )
        
        query = db.query(MedicalRecord)
        
        # 患者过滤
        if patient_id:
            query = query.filter(MedicalRecord.patient_id == patient_id)
        
        # 会话过滤
        if conversation_id:
            query = query.filter(MedicalRecord.conversation_id == conversation_id)
        
        # 审核医生过滤
        if reviewed_by:
            query = query.filter(MedicalRecord.reviewed_by == reviewed_by)
        
        # 状态过滤
        if status:
            query = query.filter(MedicalRecord.status == status)
        
        # 获取总数
        total = query.count()
        
        # 分页，按创建时间倒序
        records = (
            query.order_by(desc(MedicalRecord.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
        
        return records, total
    
    @staticmethod
    def get_conversation_records(
        conversation_id: int,
        db: Session = None,
    ) -> List[MedicalRecord]:
        """
        获取会话关联的所有病历
        
        Args:
            conversation_id: 会话ID
            db: 数据库会话
        
        Returns:
            病历列表
        """
        records, _ = MedicalRecordService.list_medical_records(
            conversation_id=conversation_id,
            skip=0,
            limit=1000,  # 一个会话通常不会有太多病历
            db=db,
        )
        return records
    
    @staticmethod
    def search_medical_records(
        keyword: str,
        skip: int = 0,
        limit: int = 100,
        patient_id: Optional[int] = None,
        conversation_id: Optional[int] = None,
        reviewed_by: Optional[int] = None,
        status: Optional[MedicalRecordStatus] = None,
        db: Session = None,
    ) -> tuple[List[MedicalRecord], int]:
        """
        搜索病历
        
        Args:
            keyword: 搜索关键词（搜索标题、主诉、诊断等）
            skip: 跳过的记录数
            limit: 返回的记录数
            patient_id: 患者ID过滤（可选）
            db: 数据库会话
        
        Returns:
            (病历列表, 总数量)
        """
        if db is None:
            with get_session() as session:
                return MedicalRecordService.search_medical_records(
                    keyword,
                    skip,
                    limit,
                    patient_id,
                    conversation_id,
                    reviewed_by,
                    status,
                    session,
                )
        
        query = db.query(MedicalRecord).filter(
            or_(
                MedicalRecord.title.ilike(f"%{keyword}%"),
                MedicalRecord.chief_complaint.ilike(f"%{keyword}%"),
                MedicalRecord.present_illness.ilike(f"%{keyword}%"),
            )
        )
        
        # 患者过滤
        if patient_id:
            query = query.filter(MedicalRecord.patient_id == patient_id)

        if conversation_id:
            query = query.filter(MedicalRecord.conversation_id == conversation_id)

        if reviewed_by:
            query = query.filter(MedicalRecord.reviewed_by == reviewed_by)

        if status:
            query = query.filter(MedicalRecord.status == status)
        
        # 获取总数
        total = query.count()
        
        # 分页，按创建时间倒序
        records = (
            query.order_by(desc(MedicalRecord.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
        
        return records, total
    
    @staticmethod
    def get_medical_record_statistics(
        patient_id: Optional[int] = None,
        doctor_id: Optional[int] = None,
        db: Session = None,
    ) -> Dict[str, Any]:
        """
        获取病历统计信息
        
        Args:
            patient_id: 患者ID（可选）
            doctor_id: 医生ID（可选）
            db: 数据库会话
        
        Returns:
            统计信息字典
        """
        if db is None:
            with get_session() as session:
                return MedicalRecordService.get_medical_record_statistics(
                    patient_id, doctor_id, session
                )
        
        query = db.query(MedicalRecord)
        
        if patient_id:
            query = query.filter(MedicalRecord.patient_id == patient_id)
        
        if doctor_id:
            query = query.filter(MedicalRecord.reviewed_by == doctor_id)
        
        total_count = query.count()
        draft_count = query.filter(
            MedicalRecord.status == MedicalRecordStatus.DRAFT
        ).count()
        confirmed_count = query.filter(
            MedicalRecord.status == MedicalRecordStatus.CONFIRMED
        ).count()
        reviewed_count = query.filter(
            MedicalRecord.status == MedicalRecordStatus.REVIEWED
        ).count()
        archived_count = query.filter(
            MedicalRecord.status == MedicalRecordStatus.ARCHIVED
        ).count()
        
        stats = {
            "total_count": total_count,
            "draft_count": draft_count,
            "confirmed_count": confirmed_count,
            "reviewed_count": reviewed_count,
            "archived_count": archived_count,
        }
        
        return stats
    
    @staticmethod
    def delete_medical_record(record_id: int, db: Session) -> bool:
        """
        删除病历（仅允许删除草稿状态的病历）
        
        Args:
            record_id: 病历ID
            db: 数据库会话
        
        Returns:
            是否删除成功
        
        Raises:
            NotFoundException: 病历不存在
            BusinessException: 病历状态不允许删除
        """
        medical_record = MedicalRecordService.get_medical_record_by_id(record_id, db)
        if not medical_record:
            raise NotFoundException(f"病历 ID {record_id} 不存在")
        
        # 只允许删除草稿状态的病历
        if medical_record.status != MedicalRecordStatus.DRAFT:
            raise BusinessException("只有草稿状态的病历才能删除")
        
        db.delete(medical_record)
        db.commit()
        
        logger.info(f"删除病历成功: ID {record_id}")
        return True


# 创建全局服务实例
medical_record_service = MedicalRecordService()


# 导出
__all__ = ["MedicalRecordService", "medical_record_service"]

