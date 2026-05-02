"""
OCR服务基类
提供统一的OCR接口
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from PIL import Image

from app.utils.logger import get_logger

logger = get_logger(__name__)


class OCRResult(BaseModel):
    """OCR识别结果"""
    text: str = Field(description="识别的文本内容")
    confidence: float = Field(default=0.0, description="置信度（0-1）")
    boxes: Optional[List[List[float]]] = Field(default=None, description="文本框坐标")
    words: Optional[List[Dict[str, Any]]] = Field(default=None, description="单词级别信息")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="元数据")


class BaseOCRService(ABC):
    """OCR服务基类"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化OCR服务
        
        Args:
            config: OCR配置字典
        """
        self.config = config or {}
        self._initialized = False
    
    @abstractmethod
    def _initialize(self):
        """初始化OCR引擎"""
        pass
    
    def _ensure_initialized(self):
        """确保OCR已初始化"""
        if not self._initialized:
            self._initialize()
            self._initialized = True
    
    @abstractmethod
    def recognize(
        self,
        image: Image.Image,
        **kwargs
    ) -> OCRResult:
        """
        识别图片中的文字（同步）
        
        Args:
            image: PIL Image对象
            **kwargs: 其他参数
            
        Returns:
            OCRResult: OCR识别结果
        """
        pass
    
    @abstractmethod
    def recognize_bytes(
        self,
        image_bytes: bytes,
        **kwargs
    ) -> OCRResult:
        """
        识别字节流中的文字
        
        Args:
            image_bytes: 图片字节流
            **kwargs: 其他参数
            
        Returns:
            OCRResult: OCR识别结果
        """
        pass
    
    @abstractmethod
    def recognize_file(
        self,
        file_path: str,
        **kwargs
    ) -> OCRResult:
        """
        识别文件中的文字
        
        Args:
            file_path: 图片文件路径
            **kwargs: 其他参数
            
        Returns:
            OCRResult: OCR识别结果
        """
        pass
    
    def batch_recognize(
        self,
        images: List[Image.Image],
        **kwargs
    ) -> List[OCRResult]:
        """
        批量识别图片
        
        Args:
            images: PIL Image对象列表
            **kwargs: 其他参数
            
        Returns:
            List[OCRResult]: OCR识别结果列表
        """
        results = []
        for image in images:
            try:
                result = self.recognize(image, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"批量识别失败: {e}", exc_info=True)
                # 返回空结果
                results.append(OCRResult(text="", confidence=0.0))
        return results
    
    def get_service_info(self) -> Dict[str, Any]:
        """获取服务信息"""
        return {
            "service_type": self.__class__.__name__,
            "initialized": self._initialized,
        }

