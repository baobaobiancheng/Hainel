"""
咨询诊断 API
基于 MDAgents 多智能体系统的症状诊断服务
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.consultation_service import consultation_service
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/consultation", tags=["咨询诊断"])


class DiagnosisRequest(BaseModel):
    """诊断请求"""
    symptoms: str = Field(..., description="患者描述的症状", min_length=2)
    medical_history: Optional[str] = Field(None, description="既往病史")
    difficulty: Optional[str] = Field(
        None,
        description="诊断复杂度，可选 basic/intermediate/advanced，默认自动判断"
    )


class DiagnosisResponse(BaseModel):
    """诊断响应"""
    success: bool
    symptoms: str
    medical_history: Optional[str]
    complexity: str
    diagnosis: str
    difficulty: str
    agents_used: int | str


@router.post(
    "/diagnosis",
    response_model=DiagnosisResponse,
    summary="症状诊断",
    description="基于 MDAgents 多智能体系统进行症状诊断和建议",
)
async def diagnose(request: DiagnosisRequest):
    """
    症状诊断接口

    - **symptoms**: 患者描述的症状（必填）
    - **medical_history**: 既往病史（可选）
    - **difficulty**: 诊断复杂度，可选 basic/intermediate/advanced，默认自动判断

    返回诊断结果和建议
    """
    try:
        logger.info(f"收到诊断请求 - 症状: {request.symptoms[:50]}...")

        result = consultation_service.diagnose(
            symptoms=request.symptoms,
            medical_history=request.medical_history,
            difficulty=request.difficulty,
        )

        return DiagnosisResponse(**result)

    except Exception as e:
        logger.error(f"诊断失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"诊断服务异常: {str(e)}"
        )


@router.get("/health", summary="健康检查")
async def health_check():
    """检查诊断服务状态"""
    return {
        "status": "ok",
        "service": "consultation",
        "model": consultation_service._model,
    }
