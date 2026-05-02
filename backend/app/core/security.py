"""
安全模块
提供JWT认证和密码加密功能
"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings
from app.core.exceptions import AuthenticationException
from app.utils.logger import get_logger

logger = get_logger(__name__)


# 密码加密上下文
pwd_context = CryptContext(
    schemes=[settings.PASSWORD_HASH_ALGORITHM],
    deprecated="auto"
)


class Security:
    """安全工具类"""
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        验证密码
        
        Args:
            plain_password: 明文密码
            hashed_password: 哈希密码
        
        Returns:
            是否匹配
        """
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            logger.error(f"密码验证失败: {e}")
            return False
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """
        生成密码哈希
        
        Args:
            password: 明文密码
        
        Returns:
            哈希密码
        """
        return pwd_context.hash(password)
    
    @staticmethod
    def create_access_token(
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        创建访问令牌
        
        Args:
            data: 要编码的数据
            expires_delta: 过期时间增量
        
        Returns:
            JWT令牌字符串
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access",
        })
        
        encoded_jwt = jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        
        return encoded_jwt
    
    @staticmethod
    def decode_token(token: str, token_type: str = "access") -> Dict[str, Any]:
        """
        解码JWT令牌
        
        Args:
            token: JWT令牌字符串
            token_type: 令牌类型（access或refresh）
        
        Returns:
            解码后的数据
        
        Raises:
            AuthenticationException: 令牌无效或过期
        """
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            
            # 验证令牌类型
            if payload.get("type") != token_type:
                raise AuthenticationException("令牌类型不匹配")
            
            return payload
        except JWTError as e:
            logger.warning(f"JWT解码失败: {e}")
            raise AuthenticationException("无效的令牌")
        except Exception as e:
            logger.error(f"令牌验证失败: {e}")
            raise AuthenticationException("令牌验证失败")
    


# 创建全局安全实例
security = Security()


# 导出
__all__ = ["security", "Security", "pwd_context"]

