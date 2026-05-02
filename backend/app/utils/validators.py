"""
数据验证工具模块
提供常用的数据验证函数
"""
import os
import re
from typing import List, Pattern
from datetime import datetime
import phonenumbers
from pydantic import EmailStr

from app.utils.logger import get_logger

logger = get_logger(__name__)


class ValidationError(Exception):
    """验证错误异常"""
    pass


# 常用正则表达式模式
PHONE_PATTERN: Pattern = re.compile(r"^1[3-9]\d{9}$")
ID_CARD_PATTERN: Pattern = re.compile(r"^[1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]$")
CHINESE_NAME_PATTERN: Pattern = re.compile(r"^[\u4e00-\u9fa5]{2,10}$")
ENGLISH_NAME_PATTERN: Pattern = re.compile(r"^[a-zA-Z\s]{2,50}$")


def validate_phone(phone: str, country_code: str = "CN") -> bool:
    """
    验证手机号
    
    Args:
        phone: 手机号
        country_code: 国家代码，默认CN（中国）
    
    Returns:
        是否有效
    """
    if not phone:
        return False
    
    try:
        # 使用phonenumbers库验证
        parsed_number = phonenumbers.parse(phone, country_code)
        return phonenumbers.is_valid_number(parsed_number)
    except Exception:
        # 如果phonenumbers失败，使用正则表达式（仅中国）
        if country_code == "CN":
            return bool(PHONE_PATTERN.match(phone))
        return False


def validate_id_card(id_card: str) -> bool:
    """
    验证身份证号（18位）
    
    Args:
        id_card: 身份证号
    
    Returns:
        是否有效
    """
    if not id_card:
        return False
    
    # 基本格式验证
    if not ID_CARD_PATTERN.match(id_card):
        return False
    
    # 校验码验证
    try:
        weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
        check_codes = ['1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2']
        
        sum_value = sum(int(id_card[i]) * weights[i] for i in range(17))
        check_code = check_codes[sum_value % 11]
        
        return id_card[17].upper() == check_code
    except Exception:
        return False


def validate_email(email: str) -> bool:
    """
    验证邮箱地址
    
    Args:
        email: 邮箱地址
    
    Returns:
        是否有效
    """
    if not email:
        return False
    
    try:
        # 使用Pydantic的EmailStr验证
        EmailStr._validate(email, None)
        return True
    except Exception:
        return False


def validate_chinese_name(name: str) -> bool:
    """
    验证中文姓名
    
    Args:
        name: 姓名
    
    Returns:
        是否有效
    """
    if not name:
        return False
    return bool(CHINESE_NAME_PATTERN.match(name))


def validate_english_name(name: str) -> bool:
    """
    验证英文姓名
    
    Args:
        name: 姓名
    
    Returns:
        是否有效
    """
    if not name:
        return False
    return bool(ENGLISH_NAME_PATTERN.match(name))


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    验证密码强度
    
    Args:
        password: 密码
    
    Returns:
        (是否有效, 错误消息)
    """
    if not password:
        return False, "密码不能为空"
    
    if len(password) < 8:
        return False, "密码长度至少8位"
    
    if len(password) > 128:
        return False, "密码长度不能超过128位"
    
    # 检查是否包含数字
    if not re.search(r"\d", password):
        return False, "密码必须包含至少一个数字"
    
    # 检查是否包含字母
    if not re.search(r"[a-zA-Z]", password):
        return False, "密码必须包含至少一个字母"
    
    # 可选：检查是否包含特殊字符
    # if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
    #     return False, "密码必须包含至少一个特殊字符"
    
    return True, "密码强度符合要求"


def validate_date_format(date_str: str, format_str: str = "%Y-%m-%d") -> bool:
    """
    验证日期格式
    
    Args:
        date_str: 日期字符串
        format_str: 日期格式
    
    Returns:
        是否有效
    """
    if not date_str:
        return False
    
    try:
        datetime.strptime(date_str, format_str)
        return True
    except ValueError:
        return False


def validate_url(url: str) -> bool:
    """
    验证URL格式
    
    Args:
        url: URL字符串
    
    Returns:
        是否有效
    """
    if not url:
        return False
    
    url_pattern = re.compile(
        r"^https?://"  # http:// or https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain...
        r"localhost|"  # localhost...
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE
    )
    return bool(url_pattern.match(url))


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除危险字符
    
    Args:
        filename: 原始文件名
    
    Returns:
        清理后的文件名
    """
    if not filename:
        return "unnamed"
    
    # 移除路径分隔符和危险字符
    dangerous_chars = ['/', '\\', '..', '<', '>', ':', '"', '|', '?', '*']
    sanitized = filename
    
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '_')
    
    # 限制长度
    if len(sanitized) > 255:
        name, ext = os.path.splitext(sanitized)
        sanitized = name[:255 - len(ext)] + ext
    
    return sanitized


def validate_file_extension(filename: str, allowed_extensions: List[str]) -> bool:
    """
    验证文件扩展名
    
    Args:
        filename: 文件名
        allowed_extensions: 允许的扩展名列表（不含点号）
    
    Returns:
        是否有效
    """
    if not filename:
        return False
    
    ext = os.path.splitext(filename)[1].lstrip('.').lower()
    return ext in [e.lower() for e in allowed_extensions]


def validate_age(age: int) -> bool:
    """
    验证年龄
    
    Args:
        age: 年龄
    
    Returns:
        是否有效（0-150）
    """
    return isinstance(age, int) and 0 <= age <= 150


def validate_gender(gender: str) -> bool:
    """
    验证性别
    
    Args:
        gender: 性别（male/female/other）
    
    Returns:
        是否有效
    """
    valid_genders = ['male', 'female', 'other', 'M', 'F', '男', '女']
    return gender in valid_genders


# 导出
__all__ = [
    "ValidationError",
    "validate_phone",
    "validate_id_card",
    "validate_email",
    "validate_chinese_name",
    "validate_english_name",
    "validate_password_strength",
    "validate_date_format",
    "validate_url",
    "sanitize_filename",
    "validate_file_extension",
    "validate_age",
    "validate_gender",
]

