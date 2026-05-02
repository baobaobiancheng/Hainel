"""
日志工具模块
提供统一的日志记录功能
"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from app.config import settings


def setup_logger(
    name: str = "medical_system",
    log_level: Optional[str] = None,
    log_file: Optional[str] = None,
    log_format: Optional[str] = None,
) -> logging.Logger:
    """
    设置并返回日志记录器
    
    Args:
        name: 日志记录器名称
        log_level: 日志级别，默认使用配置中的LOG_LEVEL
        log_file: 日志文件路径，默认使用配置中的LOG_FILE
        log_format: 日志格式，默认使用配置中的LOG_FORMAT
    
    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 设置日志级别
    level = log_level or settings.LOG_LEVEL
    logger.setLevel(getattr(logging, level))
    
    # 日志格式
    formatter = logging.Formatter(
        log_format or settings.LOG_FORMAT,
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器（如果指定了日志文件）
    log_file_path = log_file or settings.LOG_FILE
    if log_file_path:
        # 确保日志目录存在
        log_path = Path(log_file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 使用RotatingFileHandler实现日志轮转
        file_handler = RotatingFileHandler(
            log_file_path,
            maxBytes=settings.LOG_MAX_BYTES,
            backupCount=settings.LOG_BACKUP_COUNT,
            encoding="utf-8"
        )
        file_handler.setLevel(getattr(logging, level))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


# 创建默认日志记录器
logger = setup_logger()


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志记录器
    
    Args:
        name: 日志记录器名称
    
    Returns:
        日志记录器实例
    """
    return logging.getLogger(name)


# 导出
__all__ = ["logger", "get_logger", "setup_logger"]

