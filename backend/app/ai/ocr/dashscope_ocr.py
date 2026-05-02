"""
百炼平台多模态 OCR 服务

调用阿里云百炼多模态模型（qwen-plus/qwen-max 等）识别图片中的文字内容。
复用 LLM 配置中的 API Key（LLM_API_KEY）。
"""
import base64
import io
from typing import Dict, Any, Optional

from PIL import Image

from app.ai.ocr.base import BaseOCRService, OCRResult
from app.config import settings
from app.services.token_usage_service import token_usage_service
from app.utils.logger import get_logger

logger = get_logger(__name__)

# 识别提示词
_OCR_PROMPT = "这是一张医疗报告图片，请详细识别其中的所有文字内容，包括检查项目、数值、诊断结果等，按原有版式完整输出。如果图片中没有文字或文字不清晰，请说明情况。"


class DashScopeOCRService(BaseOCRService):
    """百炼平台多模态 OCR 服务"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.api_key: str = self.config.get("api_key") or settings.LLM_API_KEY or ""
        # qwen-plus 不支持图片，使用专门的视觉模型
        self.model: str = self.config.get("model") or "qwen-vl-plus"

    def _initialize(self):
        """初始化 DashScope 客户端"""
        try:
            import dashscope
            if not self.api_key:
                raise ValueError(
                    "DashScope API Key 未配置，请在 .env 文件中设置 LLM_API_KEY"
                )
            dashscope.api_key = self.api_key
            logger.info(f"DashScope OCR 服务初始化成功 (model={self.model})")
        except ImportError:
            raise ImportError(
                "dashscope 包未安装，请运行: pip install dashscope"
            )
        except Exception as e:
            logger.error(f"DashScope OCR 初始化失败: {e}", exc_info=True)
            raise

    @staticmethod
    def _image_to_base64(image: Image.Image) -> str:
        """将 PIL Image 转为 base64 字符串（JPEG 格式）"""
        buf = io.BytesIO()
        image.convert("RGB").save(buf, format="JPEG", quality=90)
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        return b64

    def _call_api(self, image: Image.Image) -> OCRResult:
        """调用 DashScope MultiModal API 执行 OCR（支持base64）"""
        self._ensure_initialized()
        from dashscope import MultiModalConversation

        # 转换为 base64
        b64_image = self._image_to_base64(image)

        messages = [
            {
                "role": "user",
                "content": [
                    {"image": f"data:image/jpeg;base64,{b64_image}"},
                    {"text": _OCR_PROMPT},
                ],
            }
        ]

        response = MultiModalConversation.call(
            model=self.model,
            messages=messages,
            api_key=self.api_key,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"DashScope OCR 调用失败: status={response.status_code}, "
                f"message={response.message}"
            )

        text = response.output.choices[0].message.content[0].get("text", "")
        usage = dict(response.usage or {})
        token_usage_service.record_usage(
            provider="dashscope",
            model_name=self.model,
            source_type="ocr_recognize",
            usage=usage,
            success=True,
        )
        return OCRResult(
            text=text.strip(),
            confidence=1.0,
            metadata={"model": self.model, "usage": usage},
        )

    def recognize(self, image: Image.Image, **kwargs) -> OCRResult:
        """识别 PIL Image 中的文字"""
        try:
            return self._call_api(image)
        except Exception as e:
            logger.error(f"DashScope OCR 识别失败: {e}", exc_info=True)
            raise

    def recognize_bytes(self, image_bytes: bytes, **kwargs) -> OCRResult:
        """识别字节流中的文字"""
        try:
            image = Image.open(io.BytesIO(image_bytes))
            return self.recognize(image, **kwargs)
        except Exception as e:
            logger.error(f"DashScope OCR 字节流识别失败: {e}", exc_info=True)
            raise

    def recognize_file(self, file_path: str, **kwargs) -> OCRResult:
        """识别本地图片文件中的文字"""
        try:
            image = Image.open(file_path)
            return self.recognize(image, **kwargs)
        except Exception as e:
            logger.error(f"DashScope OCR 文件识别失败: {e}", exc_info=True)
            raise

    def recognize_pdf(
        self,
        pdf_bytes: bytes,
        dpi: int = 200,
        **kwargs
    ) -> OCRResult:
        """
        识别PDF文档中的文字

        Args:
            pdf_bytes: PDF文件的字节内容
            dpi: 转换为图片时的分辨率，默认200

        Returns:
            OCRResult: OCR识别结果，包含多页合并后的文本
        """
        from app.utils.pdf_processor import PDFProcessor, PDFProcessorError

        try:
            # 将PDF转换为图片
            images = PDFProcessor.convert_from_bytes(pdf_bytes, dpi=dpi)
            logger.info(f"开始OCR识别PDF文档，共 {len(images)} 页")

            # 逐页识别
            page_results = []
            for i, image in enumerate(images):
                try:
                    result = self._call_api(image)
                    page_text = result.text
                    page_results.append({
                        "page": i + 1,
                        "text": page_text,
                        "confidence": result.confidence,
                    })
                    logger.info(f"第 {i+1}/{len(images)} 页识别完成")
                except Exception as e:
                    logger.error(f"第 {i+1} 页识别失败: {e}")
                    page_results.append({
                        "page": i + 1,
                        "text": "",
                        "confidence": 0.0,
                        "error": str(e),
                    })

            # 合并结果
            full_text = ""
            confidences = []
            for pr in page_results:
                if pr["text"]:
                    full_text += f"--- 第 {pr['page']} 页 ---\n{pr['text']}\n\n"
                    confidences.append(pr["confidence"])

            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            return OCRResult(
                text=full_text.strip(),
                confidence=avg_confidence,
                metadata={
                    "model": self.model,
                    "page_count": len(images),
                    "page_results": page_results,
                },
            )

        except PDFProcessorError as e:
            logger.error(f"PDF处理失败: {e}")
            raise
        except Exception as e:
            logger.error(f"PDF OCR识别失败: {e}", exc_info=True)
            raise
