"""
练习API
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.api.v1.auth import get_current_user
from app.schemas.common import ResponseModel

router = APIRouter()


@router.get("/recommend", response_model=ResponseModel[list[dict]])
async def recommend_practice_questions(
    subject: str = None,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """推荐练习题"""
    # TODO: 实现个性化推荐逻辑
    
    return ResponseModel(
        success=True,
        message="推荐成功",
        data=[],
    )


@router.post("/submit", response_model=ResponseModel[dict])
async def submit_practice_answer(
    question_id: str,
    answer: str,
    time_spent: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """提交练习答案"""
    # TODO: 实现答案提交和评估逻辑
    
    return ResponseModel(
        success=True,
        message="提交成功",
        data={
            "is_correct": True,
            "feedback": "回答正确！",
        },
    )


@router.get("/review-plan", response_model=ResponseModel[dict])
async def get_review_plan(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取复习计划"""
    # TODO: 实现复习计划生成逻辑（基于遗忘曲线）
    
    return ResponseModel(
        success=True,
        message="获取成功",
        data={
            "today": [],
            "this_week": [],
            "overdue": [],
        },
    )

