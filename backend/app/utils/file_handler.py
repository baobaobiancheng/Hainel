"""
文件处理工具模块
提供文件上传、下载、删除等功能
"""
import uuid
from pathlib import Path
from typing import Optional, List
import aiofiles
from fastapi import UploadFile

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class FileHandlerError(Exception):
    """文件处理异常"""
    pass


class FileHandler:
    """文件处理器"""
    
    def __init__(self, base_dir: Optional[str] = None):
        """
        初始化文件处理器
        
        Args:
            base_dir: 基础目录，默认使用配置中的UPLOAD_DIR
        """
        self.base_dir = Path(base_dir or settings.UPLOAD_DIR)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.max_size = settings.MAX_UPLOAD_SIZE
        self.allowed_extensions = settings.ALLOWED_EXTENSIONS
    
    def _validate_file(self, filename: str, size: int) -> None:
        """
        验证文件
        
        Args:
            filename: 文件名
            size: 文件大小（字节）
        
        Raises:
            FileHandlerError: 文件验证失败
        """
        # 检查文件大小
        if size > self.max_size:
            raise FileHandlerError(
                f"文件大小超过限制: {size} bytes > {self.max_size} bytes"
            )
        
        # 检查文件扩展名
        ext = Path(filename).suffix.lstrip(".").lower()
        if ext not in self.allowed_extensions:
            raise FileHandlerError(
                f"不支持的文件类型: {ext}，允许的类型: {self.allowed_extensions}"
            )
    
    def _generate_filename(self, original_filename: str) -> str:
        """
        生成唯一文件名
        
        Args:
            original_filename: 原始文件名
        
        Returns:
            唯一文件名
        """
        ext = Path(original_filename).suffix
        unique_id = uuid.uuid4().hex
        return f"{unique_id}{ext}"
    
    def _get_file_path(self, filename: str, subdir: Optional[str] = None) -> Path:
        """
        获取文件完整路径
        
        Args:
            filename: 文件名
            subdir: 子目录
        
        Returns:
            文件路径
        """
        if subdir:
            file_dir = self.base_dir / subdir
            file_dir.mkdir(parents=True, exist_ok=True)
        else:
            file_dir = self.base_dir
        
        return file_dir / filename
    
    async def save_upload_file(
        self,
        file: UploadFile,
        subdir: Optional[str] = None,
        custom_filename: Optional[str] = None,
    ) -> str:
        """
        保存上传的文件
        
        Args:
            file: FastAPI UploadFile对象
            subdir: 子目录
            custom_filename: 自定义文件名（可选）
        
        Returns:
            保存的文件名
        
        Raises:
            FileHandlerError: 保存失败
        """
        try:
            # 验证文件
            contents = await file.read()
            file_size = len(contents)
            self._validate_file(file.filename, file_size)
            
            # 生成文件名
            if custom_filename:
                filename = custom_filename
            else:
                filename = self._generate_filename(file.filename)
            
            # 获取文件路径
            file_path = self._get_file_path(filename, subdir)
            
            # 保存文件
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(contents)
            
            logger.info(f"文件保存成功: {file_path}")
            return filename
        except Exception as e:
            logger.error(f"保存文件失败: {e}")
            raise FileHandlerError(f"保存文件失败: {e}")
    
    def save_file(
        self,
        content: bytes,
        filename: str,
        subdir: Optional[str] = None,
    ) -> str:
        """
        保存文件内容
        
        Args:
            content: 文件内容（字节）
            filename: 文件名
            subdir: 子目录
        
        Returns:
            保存的文件名
        
        Raises:
            FileHandlerError: 保存失败
        """
        try:
            # 验证文件
            self._validate_file(filename, len(content))
            
            # 获取文件路径
            file_path = self._get_file_path(filename, subdir)
            
            # 保存文件
            with open(file_path, "wb") as f:
                f.write(content)
            
            logger.info(f"文件保存成功: {file_path}")
            return filename
        except Exception as e:
            logger.error(f"保存文件失败: {e}")
            raise FileHandlerError(f"保存文件失败: {e}")
    
    async def read_file(
        self,
        filename: str,
        subdir: Optional[str] = None,
    ) -> bytes:
        """
        读取文件内容
        
        Args:
            filename: 文件名
            subdir: 子目录
        
        Returns:
            文件内容（字节）
        
        Raises:
            FileHandlerError: 读取失败
        """
        try:
            file_path = self._get_file_path(filename, subdir)
            
            if not file_path.exists():
                raise FileHandlerError(f"文件不存在: {file_path}")
            
            async with aiofiles.open(file_path, "rb") as f:
                content = await f.read()
            
            return content
        except Exception as e:
            logger.error(f"读取文件失败: {e}")
            raise FileHandlerError(f"读取文件失败: {e}")
    
    def delete_file(
        self,
        filename: str,
        subdir: Optional[str] = None,
    ) -> bool:
        """
        删除文件
        
        Args:
            filename: 文件名
            subdir: 子目录
        
        Returns:
            是否删除成功
        """
        try:
            file_path = self._get_file_path(filename, subdir)
            
            if not file_path.exists():
                logger.warning(f"文件不存在: {file_path}")
                return False
            
            file_path.unlink()
            logger.info(f"文件删除成功: {file_path}")
            return True
        except Exception as e:
            logger.error(f"删除文件失败: {e}")
            return False
    
    def file_exists(
        self,
        filename: str,
        subdir: Optional[str] = None,
    ) -> bool:
        """
        检查文件是否存在
        
        Args:
            filename: 文件名
            subdir: 子目录
        
        Returns:
            是否存在
        """
        file_path = self._get_file_path(filename, subdir)
        return file_path.exists()
    
    def get_file_size(
        self,
        filename: str,
        subdir: Optional[str] = None,
    ) -> int:
        """
        获取文件大小
        
        Args:
            filename: 文件名
            subdir: 子目录
        
        Returns:
            文件大小（字节）
        
        Raises:
            FileHandlerError: 文件不存在
        """
        file_path = self._get_file_path(filename, subdir)
        
        if not file_path.exists():
            raise FileHandlerError(f"文件不存在: {file_path}")
        
        return file_path.stat().st_size
    
    def list_files(
        self,
        subdir: Optional[str] = None,
        pattern: Optional[str] = None,
    ) -> List[str]:
        """
        列出文件
        
        Args:
            subdir: 子目录
            pattern: 文件名模式（支持通配符）
        
        Returns:
            文件名列表
        """
        try:
            if subdir:
                dir_path = self.base_dir / subdir
            else:
                dir_path = self.base_dir
            
            if not dir_path.exists():
                return []
            
            if pattern:
                files = list(dir_path.glob(pattern))
            else:
                files = list(dir_path.iterdir())
            
            return [f.name for f in files if f.is_file()]
        except Exception as e:
            logger.error(f"列出文件失败: {e}")
            return []
    
    def get_file_path(
        self,
        filename: str,
        subdir: Optional[str] = None,
    ) -> Path:
        """
        获取文件路径对象
        
        Args:
            filename: 文件名
            subdir: 子目录
        
        Returns:
            文件路径对象
        """
        return self._get_file_path(filename, subdir)


# 创建全局文件处理器实例
file_handler = FileHandler()


# 导出
__all__ = ["file_handler", "FileHandler", "FileHandlerError"]

