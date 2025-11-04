"""
错题管理API
"""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from app.core.database import get_db
from app.core.exceptions import NotFound
from app.models.user import User
from app.models.error_question import ErrorQuestion
from app.api.v1.auth import get_current_user
from app.schemas.error_question import (
    ErrorQuestionCreate,
    ErrorQuestionUpdate,
    ErrorQuestionResponse,
    ErrorQuestionFilter,
)
from app.schemas.common import ResponseModel, PaginationParams, PaginatedResponse

router = APIRouter()


@router.post("", response_model=ResponseModel[ErrorQuestionResponse], status_code=201)
async def create_error_question(
    question_data: ErrorQuestionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建错题"""
    # 处理标签（转为JSON字符串）
    tags_str = None
    if question_data.tags:
        import json
        tags_str = json.dumps(question_data.tags, ensure_ascii=False)
    
    question = ErrorQuestion(
        user_id=current_user.id,
        subject=question_data.subject,
        chapter=question_data.chapter,
        question_text=question_data.question_text,
        question_image_url=question_data.question_image_url,
        correct_answer=question_data.correct_answer,
        user_answer=question_data.user_answer,
        explanation=question_data.explanation,
        difficulty=question_data.difficulty,
        error_type=question_data.error_type,
        tags=tags_str,
    )
    
    db.add(question)
    await db.commit()
    await db.refresh(question)
    
    return ResponseModel(
        success=True,
        message="错题创建成功",
        data=ErrorQuestionResponse.model_validate(question),
    )


@router.get("", response_model=ResponseModel[PaginatedResponse[ErrorQuestionResponse]])
async def get_error_questions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    subject: str = Query(None),
    difficulty: str = Query(None),
    error_type: str = Query(None),
    is_favorite: bool = Query(None),
    is_archived: bool = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取错题列表（分页、筛选、排序）"""
    # 构建查询
    query = select(ErrorQuestion).where(ErrorQuestion.user_id == current_user.id)
    
    # 筛选条件
    if subject:
        query = query.where(ErrorQuestion.subject == subject)
    if difficulty:
        query = query.where(ErrorQuestion.difficulty == difficulty)
    if error_type:
        query = query.where(ErrorQuestion.error_type == error_type)
    if is_favorite is not None:
        query = query.where(ErrorQuestion.is_favorite == is_favorite)
    if is_archived is not None:
        query = query.where(ErrorQuestion.is_archived == is_archived)
    
    # 排序
    if sort_order == "desc":
        query = query.order_by(getattr(ErrorQuestion, sort_by).desc())
    else:
        query = query.order_by(getattr(ErrorQuestion, sort_by).asc())
    
    # 计算总数
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # 分页
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    # 执行查询
    result = await db.execute(query)
    questions = result.scalars().all()
    
    # 转换为响应模型
    items = [ErrorQuestionResponse.model_validate(q) for q in questions]
    
    return ResponseModel(
        success=True,
        message="获取成功",
        data=PaginatedResponse.create(
            items=items,
            total=total or 0,
            page=page,
            page_size=page_size,
        ),
    )


@router.get("/{question_id}", response_model=ResponseModel[ErrorQuestionResponse])
async def get_error_question(
    question_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取错题详情"""
    result = await db.execute(
        select(ErrorQuestion).where(
            and_(
                ErrorQuestion.id == question_id,
                ErrorQuestion.user_id == current_user.id,
            )
        )
    )
    question = result.scalar_one_or_none()
    
    if not question:
        raise NotFound("错题不存在")
    
    return ResponseModel(
        success=True,
        message="获取成功",
        data=ErrorQuestionResponse.model_validate(question),
    )


@router.put("/{question_id}", response_model=ResponseModel[ErrorQuestionResponse])
async def update_error_question(
    question_id: UUID,
    question_data: ErrorQuestionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新错题"""
    result = await db.execute(
        select(ErrorQuestion).where(
            and_(
                ErrorQuestion.id == question_id,
                ErrorQuestion.user_id == current_user.id,
            )
        )
    )
    question = result.scalar_one_or_none()
    
    if not question:
        raise NotFound("错题不存在")
    
    # 更新字段
    update_data = question_data.model_dump(exclude_unset=True)
    
    # 处理标签
    if "tags" in update_data and update_data["tags"]:
        import json
        update_data["tags"] = json.dumps(update_data["tags"], ensure_ascii=False)
    
    for field, value in update_data.items():
        setattr(question, field, value)
    
    await db.commit()
    await db.refresh(question)
    
    return ResponseModel(
        success=True,
        message="更新成功",
        data=ErrorQuestionResponse.model_validate(question),
    )


@router.delete("/{question_id}", response_model=ResponseModel[None])
async def delete_error_question(
    question_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除错题"""
    result = await db.execute(
        select(ErrorQuestion).where(
            and_(
                ErrorQuestion.id == question_id,
                ErrorQuestion.user_id == current_user.id,
            )
        )
    )
    question = result.scalar_one_or_none()
    
    if not question:
        raise NotFound("错题不存在")
    
    await db.delete(question)
    await db.commit()
    
    return ResponseModel(
        success=True,
        message="删除成功",
        data=None,
    )

