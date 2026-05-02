"""
报告相关API
提供医疗报告的上传、OCR识别、查询等功能
"""
import asyncio
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.services.message_service import MessageService
from app.services.conversation_service import ConversationService
from app.schemas.message import MessageCreate, MessageResponse
from app.core.permissions import get_current_user, Role
from app.core.exceptions import (
    NotFoundException,
    ValidationException,
    AuthorizationException,
    to_http_exception,
)
from app.models.message import MessageRole, MessageType
from app.ai.ocr.base import BaseOCRService, OCRResult
from app.utils.file_handler import file_handler, FileHandlerError
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/reports", tags=["报告"])

# OCR服务实例（延迟初始化）
_ocr_service: Optional[BaseOCRService] = None


def get_ocr_service() -> BaseOCRService:
    """获取OCR服务实例（单例模式）"""
    global _ocr_service
    if _ocr_service is None:
        from app.ai.ocr.dashscope_ocr import DashScopeOCRService
        _ocr_service = DashScopeOCRService()
    return _ocr_service


@router.post("/upload", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def upload_report(
    conversation_id: int = Form(..., description="会话ID"),
    report_type: Optional[str] = Form(None, description="报告类型"),
    file: UploadFile = File(..., description="报告文件（图片或PDF）"),
    auto_ocr: bool = Form(True, description="是否自动OCR识别"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    上传医疗报告
    
    支持图片格式（jpg, png等）和PDF格式
    上传后可以选择自动OCR识别
    
    Args:
        conversation_id: 会话ID
        file: 报告文件
        auto_ocr: 是否自动OCR识别
        current_user: 当前用户信息
        db: 数据库会话
    
    Returns:
        创建的消息信息（包含文件URL和OCR结果）
    
    Raises:
        404: 会话不存在
        400: 文件格式不支持或文件过大
        403: 无权在该会话中上传报告
    """
    try:
        user_id = current_user.get("id")
        user_role = current_user.get("role")
        
        # 验证会话是否存在并检查权限
        conversation = ConversationService.get_conversation_by_id(conversation_id, db)
        if not conversation:
            raise NotFoundException(f"会话 ID {conversation_id} 不存在")
        
        # 权限检查
        if user_role == Role.PATIENT.value:
            if conversation.patient_id != user_id:
                raise AuthorizationException("无权在该会话中上传报告")
        elif user_role == Role.DOCTOR.value:
            if conversation.doctor_id != user_id:
                raise AuthorizationException("无权在该会话中上传报告")
        
        # 保存文件
        try:
            filename = await file_handler.save_upload_file(
                file, subdir=f"reports/{conversation_id}"
            )
            file_path = file_handler.get_file_path(filename, subdir=f"reports/{conversation_id}")
            file_size = file_handler.get_file_size(filename, subdir=f"reports/{conversation_id}")
        except FileHandlerError as e:
            raise ValidationException(f"文件保存失败: {e}")
        
        # 构建文件URL（实际应用中应该使用CDN或对象存储）
        file_url = f"/api/v1/reports/files/{conversation_id}/{filename}"
        
        # OCR识别（如果启用）
        ocr_result: Optional[OCRResult] = None
        ocr_text = ""
        file_ext = file.filename.split(".")[-1].lower() if file.filename else ""
        if auto_ocr:
            try:
                # 读取文件内容
                file_content = await file_handler.read_file(
                    filename, subdir=f"reports/{conversation_id}"
                )
                
                # 判断文件类型
                if file_ext in ["jpg", "jpeg", "png", "bmp"]:
                    # 图片文件，直接OCR识别（使用本地URL）
                    ocr_service = get_ocr_service()
                    # 构建本地HTTP URL
                    image_url = f"http://localhost:8001/uploads/reports/{conversation_id}/{filename}"
                    # 图片OCR添加30秒超时
                    try:
                        ocr_result = await asyncio.wait_for(
                            asyncio.to_thread(ocr_service.recognize_bytes, file_content),
                            timeout=30.0
                        )
                        ocr_text = ocr_result.text
                    except asyncio.TimeoutError:
                        logger.warning("图片OCR识别超时，跳过OCR")
                        ocr_text = ""
                elif file_ext == "pdf":
                    # PDF文件，转换为图片后OCR识别
                    from app.utils.pdf_processor import PDFProcessor
                    if not PDFProcessor.is_available():
                        logger.warning("pypdfium2未安装，PDF OCR功能不可用")
                        ocr_text = ""
                    else:
                        try:
                            # OCR处理添加60秒超时，避免长时间卡住
                            ocr_service = get_ocr_service()
                            try:
                                ocr_result = await asyncio.wait_for(
                                    asyncio.to_thread(ocr_service.recognize_pdf, file_content),
                                    timeout=60.0
                                )
                                ocr_text = ocr_result.text
                                # 将页数信息保存到metadata
                                page_count = ocr_result.metadata.get("page_count", 1) if ocr_result.metadata else 1
                                logger.info(f"PDF OCR识别完成，共 {page_count} 页")
                            except asyncio.TimeoutError:
                                logger.warning("PDF OCR识别超时，跳过OCR")
                                ocr_text = ""
                        except Exception as e:
                            logger.error(f"PDF OCR识别失败: {e}")
                            ocr_text = ""
                else:
                    logger.warning(f"不支持的文件类型进行OCR: {file_ext}")
                    ocr_text = ""
            except Exception as e:
                logger.error(f"OCR识别失败: {e}", exc_info=True)
                ocr_text = ""
        
        # 创建消息记录
        message_data = MessageCreate(
            conversation_id=conversation_id,
            role=MessageRole.USER.value,
            message_type=MessageType.FILE.value,
            content=f"上传报告: {file.filename}",
            file_url=file_url,
            file_name=file.filename,
            file_size=file_size,
            file_type=file.content_type,
            metadata={
                "ocr_result": {
                    "text": ocr_text,
                    "confidence": ocr_result.confidence if ocr_result else 0.0,
                    "page_count": ocr_result.metadata.get("page_count", 1) if ocr_result and ocr_result.metadata else None,
                } if ocr_result else None,
                "auto_ocr": auto_ocr,
                "file_type": file_ext,
                "report_type": report_type,
                "file_name": file.filename,
            },
        )
        
        message = MessageService.create_message(
            message_data, user_id=user_id, db=db
        )
        
        return MessageResponse.model_validate(message)
    except NotFoundException as e:
        raise to_http_exception(e)
    except ValidationException as e:
        raise to_http_exception(e)
    except AuthorizationException as e:
        raise to_http_exception(e)
    except Exception as e:
        logger.error(f"上传报告失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="上传报告失败"
        )


@router.post("/{message_id}/ocr", response_model=dict)
async def recognize_report(
    message_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    对已上传的报告进行OCR识别
    
    Args:
        message_id: 消息ID（包含报告文件）
        current_user: 当前用户信息
        db: 数据库会话
    
    Returns:
        OCR识别结果
    
    Raises:
        404: 消息不存在或不是文件消息
        400: OCR识别失败
    """
    try:
        message = MessageService.get_message_by_id(message_id, db)
        if not message:
            raise NotFoundException(f"消息 ID {message_id} 不存在")
        
        if message.message_type != MessageType.FILE:
            raise ValidationException("该消息不是文件消息")
        
        if not message.file_url:
            raise ValidationException("文件URL不存在")
        
        # 从file_url提取文件路径
        # file_url格式: /api/v1/reports/files/{conversation_id}/{filename}
        parts = message.file_url.split("/")
        if len(parts) < 5:
            raise ValidationException("无效的文件URL格式")
        
        conversation_id = parts[-2]
        filename = parts[-1]
        
        # 读取文件
        try:
            file_content = await file_handler.read_file(
                filename, subdir=f"reports/{conversation_id}"
            )
        except FileHandlerError as e:
            raise NotFoundException(f"文件不存在: {e}")
        
        # OCR识别
        try:
            ocr_service = get_ocr_service()
            ocr_result = ocr_service.recognize_bytes(file_content)
            
            # 更新消息的OCR结果
            if message.extra_metadata is None:
                message.extra_metadata = {}
            message.extra_metadata["ocr_result"] = {
                "text": ocr_result.text,
                "confidence": ocr_result.confidence,
            }
            
            # 更新消息内容（追加OCR结果）
            if ocr_result.text:
                message.content = f"{message.content}\n\nOCR识别结果:\n{ocr_result.text}"
            
            db.commit()
            db.refresh(message)
            
            return {
                "message_id": message_id,
                "ocr_result": {
                    "text": ocr_result.text,
                    "confidence": ocr_result.confidence,
                },
            }
        except Exception as e:
            logger.error(f"OCR识别失败: {e}", exc_info=True)
            raise ValidationException(f"OCR识别失败: {e}")
    except NotFoundException as e:
        raise to_http_exception(e)
    except ValidationException as e:
        raise to_http_exception(e)
    except Exception as e:
        logger.error(f"OCR识别失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OCR识别失败"
        )


@router.get("/files/{conversation_id}/{filename}")
async def download_report(
    conversation_id: int,
    filename: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    下载报告文件
    
    Args:
        conversation_id: 会话ID
        filename: 文件名
        current_user: 当前用户信息
        db: 数据库会话
    
    Returns:
        文件内容
    
    Raises:
        404: 文件不存在
        403: 无权访问该文件
    """
    try:
        user_id = current_user.get("id")
        user_role = current_user.get("role")
        
        # 验证会话权限
        conversation = ConversationService.get_conversation_by_id(conversation_id, db)
        if not conversation:
            raise NotFoundException(f"会话 ID {conversation_id} 不存在")
        
        # 权限检查
        if user_role == Role.PATIENT.value:
            if conversation.patient_id != user_id:
                raise AuthorizationException("无权访问该文件")
        elif user_role == Role.DOCTOR.value:
            if conversation.doctor_id != user_id and conversation.doctor_id is not None:
                raise AuthorizationException("无权访问该文件")
        
        # 读取文件
        try:
            file_content = await file_handler.read_file(
                filename, subdir=f"reports/{conversation_id}"
            )
        except FileHandlerError as e:
            raise NotFoundException(f"文件不存在: {e}")
        
        # 返回文件（需要设置正确的Content-Type）
        from fastapi.responses import Response
        return Response(
            content=file_content,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )
    except NotFoundException as e:
        raise to_http_exception(e)
    except AuthorizationException as e:
        raise to_http_exception(e)
    except Exception as e:
        logger.error(f"下载文件失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="下载文件失败"
        )


# 导出
__all__ = ["router"]

