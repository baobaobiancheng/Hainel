"""
用药提醒 API
提供用药/检查/复诊提醒的完整 CRUD 功能
"""
from datetime import datetime, time
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.models.reminder import Reminder
from app.models.enums import ReminderFrequency, ReminderStatus, ReminderType
from app.schemas.reminder import ReminderCreate, ReminderUpdate, ReminderResponse, ReminderListResponse
from app.core.permissions import get_current_user
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/reminders", tags=["用药提醒"])


def _parse_reminder_due_at(reminder: Reminder) -> Optional[datetime]:
    """解析一次性提醒的到期时间。"""
    if not reminder.start_date or not reminder.remind_time:
        return None

    try:
        hour, minute = reminder.remind_time[:5].split(":")
        remind_time = time(hour=int(hour), minute=int(minute))
    except (ValueError, TypeError):
        return None

    return datetime.combine(reminder.start_date.date(), remind_time)


def _complete_due_once_reminders(user_id: int, db: Session) -> None:
    """将已到设定时间的一次性提醒自动标记为已完成。"""
    due_reminders = (
        db.query(Reminder)
        .filter(
            Reminder.user_id == user_id,
            Reminder.frequency == ReminderFrequency.ONCE,
            Reminder.status == ReminderStatus.ACTIVE,
            Reminder.start_date.isnot(None),
            Reminder.remind_time.isnot(None),
        )
        .all()
    )

    changed = False
    now = datetime.now()
    for reminder in due_reminders:
        due_at = _parse_reminder_due_at(reminder)
        if due_at and due_at <= now:
            reminder.status = ReminderStatus.COMPLETED
            changed = True

    if changed:
        db.commit()


@router.post("/", response_model=ReminderResponse, status_code=status.HTTP_201_CREATED)
async def create_reminder(
    reminder_data: ReminderCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    创建提醒

    - **title**: 提醒标题（必填）
    - **reminder_type**: 类型 medication / examination / follow_up
    - **frequency**: 频率 daily / twice_daily / three_times_daily / weekly / once / custom
    - **remind_time**: 提醒时间，格式 HH:MM（如 08:00）
    """
    user_id = current_user.get("id")
    try:
        reminder = Reminder(
            **reminder_data.model_dump(),
            user_id=user_id,
        )
        db.add(reminder)
        db.commit()
        db.refresh(reminder)
        logger.info(f"用户 {user_id} 创建提醒: id={reminder.id}, title={reminder.title}")
        return ReminderResponse.model_validate(reminder)
    except Exception as e:
        db.rollback()
        logger.error(f"创建提醒失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建提醒失败，请稍后重试",
        )


@router.get("/", response_model=ReminderListResponse)
async def list_reminders(
    reminder_status: Optional[ReminderStatus] = Query(None, alias="status", description="状态过滤"),
    reminder_type: Optional[ReminderType] = Query(None, description="类型过滤"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取当前用户的提醒列表（支持状态/类型过滤和分页）
    """
    user_id = current_user.get("id")
    _complete_due_once_reminders(user_id, db)
    query = db.query(Reminder).filter(Reminder.user_id == user_id)

    if reminder_status:
        query = query.filter(Reminder.status == reminder_status)
    if reminder_type:
        query = query.filter(Reminder.reminder_type == reminder_type)

    total = query.count()
    reminders = (
        query.order_by(Reminder.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return ReminderListResponse(
        items=[ReminderResponse.model_validate(r) for r in reminders],
        total=total,
    )


@router.get("/{reminder_id}", response_model=ReminderResponse)
async def get_reminder(
    reminder_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取指定提醒详情"""
    user_id = current_user.get("id")
    _complete_due_once_reminders(user_id, db)
    reminder = (
        db.query(Reminder)
        .filter(Reminder.id == reminder_id, Reminder.user_id == user_id)
        .first()
    )
    if not reminder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="提醒不存在")
    return ReminderResponse.model_validate(reminder)


@router.put("/{reminder_id}", response_model=ReminderResponse)
async def update_reminder(
    reminder_id: int,
    reminder_data: ReminderUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新提醒信息（支持部分更新）"""
    user_id = current_user.get("id")
    reminder = (
        db.query(Reminder)
        .filter(Reminder.id == reminder_id, Reminder.user_id == user_id)
        .first()
    )
    if not reminder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="提醒不存在")

    try:
        update_data = reminder_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(reminder, key, value)

        db.commit()
        db.refresh(reminder)
        logger.info(f"用户 {user_id} 更新提醒: id={reminder_id}")
        return ReminderResponse.model_validate(reminder)
    except Exception as e:
        db.rollback()
        logger.error(f"更新提醒失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新提醒失败，请稍后重试",
        )


@router.patch("/{reminder_id}/status", response_model=ReminderResponse)
async def update_reminder_status(
    reminder_id: int,
    new_status: ReminderStatus = Query(..., description="新状态"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """快速更新提醒状态（激活/暂停/完成/取消）"""
    user_id = current_user.get("id")
    reminder = (
        db.query(Reminder)
        .filter(Reminder.id == reminder_id, Reminder.user_id == user_id)
        .first()
    )
    if not reminder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="提醒不存在")

    reminder.status = new_status
    db.commit()
    db.refresh(reminder)
    return ReminderResponse.model_validate(reminder)


@router.delete("/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reminder(
    reminder_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除指定提醒"""
    user_id = current_user.get("id")
    reminder = (
        db.query(Reminder)
        .filter(Reminder.id == reminder_id, Reminder.user_id == user_id)
        .first()
    )
    if not reminder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="提醒不存在")

    try:
        db.delete(reminder)
        db.commit()
        logger.info(f"用户 {user_id} 删除提醒: id={reminder_id}")
    except Exception as e:
        db.rollback()
        logger.error(f"删除提醒失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除提醒失败，请稍后重试",
        )


# 导出
__all__ = ["router"]
