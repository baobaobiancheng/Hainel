"""
PDF处理工具类
将PDF文档转换为图片，供OCR识别使用
使用 pypdfium2 作为后端，无需额外安装 poppler
"""
from typing import List
from PIL import Image
import logging

logger = logging.getLogger(__name__)

# 尝试导入 pypdfium2
try:
    import pypdfium2 as pdfium
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    logger.warning("pypdfium2未安装，PDF转图片功能不可用")


class PDFProcessorError(Exception):
    """PDF处理异常"""
    pass


class PDFProcessor:
    """PDF处理器 - 将PDF转换为PIL Image列表"""

    @staticmethod
    def is_available() -> bool:
        """检查PDF处理是否可用"""
        return PDF2IMAGE_AVAILABLE

    @staticmethod
    def ensure_available():
        """确保PDF处理可用，否则抛出异常"""
        if not PDF2IMAGE_AVAILABLE:
            raise PDFProcessorError(
                "pypdfium2库未安装，请运行: pip install pypdfium2"
            )

    @staticmethod
    def _render_page(pdf_doc, page_index: int, dpi: int) -> Image.Image:
        """
        渲染PDF单个页面为图片

        Args:
            pdf_doc: PDF文档对象
            page_index: 页码索引（从0开始）
            dpi: 分辨率

        Returns:
            PIL Image对象
        """
        # 获取页面
        page = pdf_doc[page_index]

        # 计算缩放因子 (72 DPI 为基础)
        scale = dpi / 72.0

        # 渲染页面到位图
        bitmap = page.render(scale=scale)

        # 转换为 PIL Image
        pil_image = bitmap.to_pil()

        # 关闭位图释放资源
        bitmap.close()

        return pil_image

    @staticmethod
    def convert_from_bytes(pdf_bytes: bytes, dpi: int = 200) -> List[Image.Image]:
        """
        从字节流转换PDF为图片列表

        Args:
            pdf_bytes: PDF文件的字节内容
            dpi: 输出图片的分辨率，默认200

        Returns:
            List[Image.Image]: 每一页对应的PIL Image对象列表

        Raises:
            PDFProcessorError: pypdfium2未安装或转换失败
        """
        PDFProcessor.ensure_available()

        try:
            # 创建 PDF 文档
            pdf_doc = pdfium.PdfDocument(pdf_bytes)
            page_count = len(pdf_doc)

            images = []
            for i in range(page_count):
                try:
                    image = PDFProcessor._render_page(pdf_doc, i, dpi)
                    images.append(image)
                except Exception as e:
                    logger.error(f"渲染第 {i+1} 页失败: {e}")
                    raise PDFProcessorError(f"渲染第 {i+1} 页失败: {e}")

            logger.info(f"PDF转换成功，共 {len(images)} 页")
            return images
        except PDFProcessorError:
            raise
        except Exception as e:
            logger.error(f"PDF转换失败: {e}")
            raise PDFProcessorError(f"PDF转换失败: {e}")

    @staticmethod
    def convert_from_file(file_path: str, dpi: int = 200) -> List[Image.Image]:
        """
        从文件路径转换PDF为图片列表

        Args:
            file_path: PDF文件的本地路径
            dpi: 输出图片的分辨率，默认200

        Returns:
            List[Image.Image]: 每一页对应的PIL Image对象列表

        Raises:
            PDFProcessorError: pypdfium2未安装或转换失败
        """
        PDFProcessor.ensure_available()

        try:
            with open(file_path, "rb") as f:
                pdf_bytes = f.read()
            return PDFProcessor.convert_from_bytes(pdf_bytes, dpi=dpi)
        except PDFProcessorError:
            raise
        except Exception as e:
            logger.error(f"PDF转换失败: {e}")
            raise PDFProcessorError(f"PDF转换失败: {e}")

    @staticmethod
    def get_page_count(pdf_bytes: bytes) -> int:
        """
        获取PDF页数

        Args:
            pdf_bytes: PDF文件的字节内容

        Returns:
            int: PDF页数
        """
        PDFProcessor.ensure_available()

        try:
            pdf_doc = pdfium.PdfDocument(pdf_bytes)
            return len(pdf_doc)
        except Exception as e:
            logger.error(f"获取PDF页数失败: {e}")
            raise PDFProcessorError(f"获取PDF页数失败: {e}")
