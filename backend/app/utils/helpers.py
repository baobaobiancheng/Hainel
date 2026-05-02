"""
辅助函数模块
提供常用的辅助函数
"""
import hashlib
import secrets
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from functools import wraps
import json

from app.utils.logger import get_logger

logger = get_logger(__name__)


def generate_random_string(length: int = 32) -> str:
    """
    生成随机字符串
    
    Args:
        length: 字符串长度
    
    Returns:
        随机字符串
    """
    return secrets.token_urlsafe(length)


def generate_uuid() -> str:
    """
    生成UUID字符串
    
    Returns:
        UUID字符串
    """
    import uuid
    return str(uuid.uuid4())


def md5_hash(text: str) -> str:
    """
    计算MD5哈希值
    
    Args:
        text: 文本
    
    Returns:
        MD5哈希值
    """
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def sha256_hash(text: str) -> str:
    """
    计算SHA256哈希值
    
    Args:
        text: 文本
    
    Returns:
        SHA256哈希值
    """
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    格式化日期时间
    
    Args:
        dt: 日期时间对象
        format_str: 格式字符串
    
    Returns:
        格式化后的字符串
    """
    return dt.strftime(format_str)


def parse_datetime(date_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> Optional[datetime]:
    """
    解析日期时间字符串
    
    Args:
        date_str: 日期时间字符串
        format_str: 格式字符串
    
    Returns:
        日期时间对象，解析失败返回None
    """
    try:
        return datetime.strptime(date_str, format_str)
    except ValueError:
        return None


def get_timestamp() -> int:
    """
    获取当前时间戳（秒）
    
    Returns:
        时间戳
    """
    return int(time.time())


def get_timestamp_ms() -> int:
    """
    获取当前时间戳（毫秒）
    
    Returns:
        时间戳（毫秒）
    """
    return int(time.time() * 1000)


def timestamp_to_datetime(timestamp: Union[int, float]) -> datetime:
    """
    时间戳转换为日期时间
    
    Args:
        timestamp: 时间戳（秒或毫秒）
    
    Returns:
        日期时间对象
    """
    # 如果时间戳大于10^10，认为是毫秒
    if timestamp > 10**10:
        timestamp = timestamp / 1000
    return datetime.fromtimestamp(timestamp)


def datetime_to_timestamp(dt: datetime) -> int:
    """
    日期时间转换为时间戳（秒）
    
    Args:
        dt: 日期时间对象
    
    Returns:
        时间戳
    """
    return int(dt.timestamp())


def deep_merge_dict(dict1: Dict, dict2: Dict) -> Dict:
    """
    深度合并字典
    
    Args:
        dict1: 字典1
        dict2: 字典2
    
    Returns:
        合并后的字典
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dict(result[key], value)
        else:
            result[key] = value
    
    return result


def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """
    安全地解析JSON字符串
    
    Args:
        json_str: JSON字符串
        default: 解析失败时的默认值
    
    Returns:
        解析后的对象
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_json_dumps(obj: Any, default: str = "{}") -> str:
    """
    安全地将对象转换为JSON字符串
    
    Args:
        obj: 要转换的对象
        default: 转换失败时的默认值
    
    Returns:
        JSON字符串
    """
    try:
        return json.dumps(obj, ensure_ascii=False)
    except (TypeError, ValueError):
        return default


def chunk_list(lst: List, chunk_size: int) -> List[List]:
    """
    将列表分割成指定大小的块
    
    Args:
        lst: 列表
        chunk_size: 块大小
    
    Returns:
        块列表
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def remove_none_values(data: Dict) -> Dict:
    """
    移除字典中的None值
    
    Args:
        data: 字典
    
    Returns:
        清理后的字典
    """
    return {k: v for k, v in data.items() if v is not None}


def get_nested_value(data: Dict, keys: Union[str, List[str]], default: Any = None) -> Any:
    """
    获取嵌套字典的值
    
    Args:
        data: 字典
        keys: 键路径（字符串用点分隔，或列表）
        default: 默认值
    
    Returns:
        值
    
    Example:
        get_nested_value({"a": {"b": {"c": 1}}}, "a.b.c")  # 返回 1
        get_nested_value({"a": {"b": {"c": 1}}}, ["a", "b", "c"])  # 返回 1
    """
    if isinstance(keys, str):
        keys = keys.split('.')
    
    value = data
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
    return value


def set_nested_value(data: Dict, keys: Union[str, List[str]], value: Any) -> None:
    """
    设置嵌套字典的值
    
    Args:
        data: 字典
        keys: 键路径（字符串用点分隔，或列表）
        value: 值
    
    Example:
        data = {}
        set_nested_value(data, "a.b.c", 1)
        # data = {"a": {"b": {"c": 1}}}
    """
    if isinstance(keys, str):
        keys = keys.split('.')
    
    for key in keys[:-1]:
        if key not in data:
            data[key] = {}
        data = data[key]
    
    data[keys[-1]] = value


def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    重试装饰器
    
    Args:
        max_attempts: 最大尝试次数
        delay: 初始延迟（秒）
        backoff: 延迟倍数
    
    Usage:
        @retry(max_attempts=3, delay=1.0)
        def my_function():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"函数 {func.__name__} 第 {attempt + 1} 次尝试失败，"
                            f"{current_delay}秒后重试: {e}"
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"函数 {func.__name__} 所有尝试均失败")
            
            raise last_exception
        return wrapper
    return decorator


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小
    
    Args:
        size_bytes: 字节数
    
    Returns:
        格式化后的字符串（如：1.5 MB）
    """
    if size_bytes == 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    return f"{size:.2f} {units[unit_index]}"


def mask_sensitive_data(data: str, mask_char: str = "*", keep_start: int = 3, keep_end: int = 4) -> str:
    """
    掩码敏感数据
    
    Args:
        data: 原始数据
        mask_char: 掩码字符
        keep_start: 保留开头字符数
        keep_end: 保留结尾字符数
    
    Returns:
        掩码后的数据
    
    Example:
        mask_sensitive_data("13812345678")  # 返回 "138****5678"
    """
    if not data or len(data) <= keep_start + keep_end:
        return mask_char * len(data) if data else ""
    
    return data[:keep_start] + mask_char * (len(data) - keep_start - keep_end) + data[-keep_end:]


def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """
    截断字符串
    
    Args:
        text: 原始文本
        max_length: 最大长度
        suffix: 后缀
    
    Returns:
        截断后的字符串
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


# 导出
__all__ = [
    "generate_random_string",
    "generate_uuid",
    "md5_hash",
    "sha256_hash",
    "format_datetime",
    "parse_datetime",
    "get_timestamp",
    "get_timestamp_ms",
    "timestamp_to_datetime",
    "datetime_to_timestamp",
    "deep_merge_dict",
    "safe_json_loads",
    "safe_json_dumps",
    "chunk_list",
    "remove_none_values",
    "get_nested_value",
    "set_nested_value",
    "retry",
    "format_file_size",
    "mask_sensitive_data",
    "truncate_string",
]

