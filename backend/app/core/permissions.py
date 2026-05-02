"""
权限管理模块
实现基于角色的访问控制（RBAC）
"""
from enum import Enum
from typing import List, Set, Optional, Dict
from fastapi import Depends, Header

from app.core.exceptions import AuthorizationException, AuthenticationException
from app.core.security import Security
from app.utils.logger import get_logger

logger = get_logger(__name__)


class Role(str, Enum):
    """用户角色枚举"""
    PATIENT = "patient"  # 患者
    DOCTOR = "doctor"  # 医生
    ADMIN = "admin"  # 管理员


class Permission(str, Enum):
    """权限枚举"""
    # 患者权限
    PATIENT_CONSULT = "patient:consult"  # 咨询
    PATIENT_UPLOAD_REPORT = "patient:upload_report"  # 上传报告
    PATIENT_VIEW_RECORDS = "patient:view_records"  # 查看病历
    
    # 医生权限
    DOCTOR_VIEW_PATIENTS = "doctor:view_patients"  # 查看患者列表
    DOCTOR_VIEW_CONVERSATIONS = "doctor:view_conversations"  # 查看会话
    DOCTOR_EDIT_RECORDS = "doctor:edit_records"  # 编辑病历
    DOCTOR_APPROVE_RECORDS = "doctor:approve_records"  # 审核病历
    DOCTOR_QUERY_KNOWLEDGE = "doctor:query_knowledge"  # 查询知识库
    
    # 管理员权限
    ADMIN_MANAGE_USERS = "admin:manage_users"  # 管理用户
    ADMIN_MANAGE_AGENTS = "admin:manage_agents"  # 管理智能体
    ADMIN_VIEW_LOGS = "admin:view_logs"  # 查看日志
    ADMIN_SYSTEM_CONFIG = "admin:system_config"  # 系统配置


# 角色权限映射
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.PATIENT: {
        Permission.PATIENT_CONSULT,
        Permission.PATIENT_UPLOAD_REPORT,
        Permission.PATIENT_VIEW_RECORDS,
    },
    Role.DOCTOR: {
        Permission.PATIENT_CONSULT,  # 医生也可以咨询
        Permission.DOCTOR_VIEW_PATIENTS,
        Permission.DOCTOR_VIEW_CONVERSATIONS,
        Permission.DOCTOR_EDIT_RECORDS,
        Permission.DOCTOR_APPROVE_RECORDS,
        Permission.DOCTOR_QUERY_KNOWLEDGE,
    },
    Role.ADMIN: {
        # 管理员拥有所有权限
        Permission.PATIENT_CONSULT,
        Permission.PATIENT_UPLOAD_REPORT,
        Permission.PATIENT_VIEW_RECORDS,
        Permission.DOCTOR_VIEW_PATIENTS,
        Permission.DOCTOR_VIEW_CONVERSATIONS,
        Permission.DOCTOR_EDIT_RECORDS,
        Permission.DOCTOR_APPROVE_RECORDS,
        Permission.DOCTOR_QUERY_KNOWLEDGE,
        Permission.ADMIN_MANAGE_USERS,
        Permission.ADMIN_MANAGE_AGENTS,
        Permission.ADMIN_VIEW_LOGS,
        Permission.ADMIN_SYSTEM_CONFIG,
    },
}


class PermissionChecker:
    """权限检查器"""
    
    @staticmethod
    def get_user_permissions(role: Role) -> Set[Permission]:
        """
        获取角色的权限集合
        
        Args:
            role: 用户角色
        
        Returns:
            权限集合
        """
        return ROLE_PERMISSIONS.get(role, set())
    
    @staticmethod
    def has_permission(user_role: Role, permission: Permission) -> bool:
        """
        检查用户是否有指定权限
        
        Args:
            user_role: 用户角色
            permission: 权限
        
        Returns:
            是否有权限
        """
        user_permissions = PermissionChecker.get_user_permissions(user_role)
        return permission in user_permissions
    
    @staticmethod
    def has_any_permission(user_role: Role, permissions: List[Permission]) -> bool:
        """
        检查用户是否有任一权限
        
        Args:
            user_role: 用户角色
            permissions: 权限列表
        
        Returns:
            是否有任一权限
        """
        user_permissions = PermissionChecker.get_user_permissions(user_role)
        return bool(user_permissions & set(permissions))
    
    @staticmethod
    def has_all_permissions(user_role: Role, permissions: List[Permission]) -> bool:
        """
        检查用户是否有所有权限
        
        Args:
            user_role: 用户角色
            permissions: 权限列表
        
        Returns:
            是否有所有权限
        """
        user_permissions = PermissionChecker.get_user_permissions(user_role)
        return set(permissions).issubset(user_permissions)
    
    @staticmethod
    def require_role(user_role: Role, allowed_roles: List[Role]) -> bool:
        """
        检查用户角色是否在允许的角色列表中
        
        Args:
            user_role: 用户角色
            allowed_roles: 允许的角色列表
        
        Returns:
            是否允许
        """
        return user_role in allowed_roles


# 创建全局权限检查器实例
permission_checker = PermissionChecker()


# 辅助函数：从请求头获取token
def get_token_from_header(authorization: Optional[str] = Header(None)) -> str:
    """
    从请求头获取token
    
    Args:
        authorization: Authorization请求头
    
    Returns:
        JWT token字符串
    
    Raises:
        AuthenticationException: 认证头无效或缺失
    """
    if not authorization:
        raise AuthenticationException("缺少认证头")
    
    if not authorization.startswith("Bearer "):
        raise AuthenticationException("无效的认证头格式，需要 'Bearer <token>'")
    
    return authorization[7:]


def get_current_user(token: str = Depends(get_token_from_header)) -> dict:
    """
    获取当前用户
    
    从JWT token中解析用户ID，并从数据库获取用户信息
    
    Args:
        token: JWT token
    
    Returns:
        用户信息字典，包含id、role等字段
    
    Raises:
        AuthenticationException: 令牌无效或用户不存在
    """
    try:
        # 解码token
        payload = Security.decode_token(token)
        user_id = payload.get("sub") or payload.get("user_id")
        
        if not user_id:
            raise AuthenticationException("令牌中缺少用户ID")
        
        # 从token中返回用户信息（避免循环依赖，实际使用时可以在API层从数据库获取）
        # 注意：这里返回的是从token中解析的信息，如果需要完整的用户信息，应该在API层调用UserService
        return {
            "id": int(user_id) if isinstance(user_id, str) else user_id,
            "role": payload.get("role", Role.PATIENT.value),
            "username": payload.get("username", ""),
        }
    except AuthenticationException:
        raise
    except Exception as e:
        logger.error(f"获取当前用户失败: {e}")
        raise AuthenticationException("获取用户信息失败")


# 权限依赖注入函数
def require_permission(permission: Permission):
    """
    权限依赖注入装饰器
    
    Args:
        permission: 需要的权限
    
    Usage:
        @app.get("/api/patients")
        async def get_patients(
            current_user: dict = Depends(get_current_user),
            _: None = Depends(require_permission(Permission.DOCTOR_VIEW_PATIENTS))
        ):
            ...
    """
    def permission_dependency(current_user: dict = Depends(get_current_user)):
        user_role_str = current_user.get("role")
        try:
            user_role = Role(user_role_str)
        except ValueError:
            raise AuthorizationException(f"无效的用户角色: {user_role_str}")
        
        if not permission_checker.has_permission(user_role, permission):
            raise AuthorizationException(
                f"缺少权限: {permission.value}",
                details={"required_permission": permission.value}
            )
        return None
    
    return permission_dependency


def require_any_permission(permissions: List[Permission]):
    """
    需要任一权限的依赖注入
    
    Args:
        permissions: 权限列表
    """
    def permission_dependency(current_user: dict = Depends(get_current_user)):
        user_role_str = current_user.get("role")
        try:
            user_role = Role(user_role_str)
        except ValueError:
            raise AuthorizationException(f"无效的用户角色: {user_role_str}")
        
        if not permission_checker.has_any_permission(user_role, permissions):
            raise AuthorizationException(
                f"缺少权限，需要以下任一权限: {[p.value for p in permissions]}",
                details={"required_permissions": [p.value for p in permissions]}
            )
        return None
    
    return permission_dependency


def require_role(allowed_roles: List[Role]):
    """
    需要特定角色的依赖注入
    
    Args:
        allowed_roles: 允许的角色列表
    """
    def role_dependency(current_user: dict = Depends(get_current_user)):
        user_role_str = current_user.get("role")
        try:
            user_role = Role(user_role_str)
        except ValueError:
            raise AuthorizationException(f"无效的用户角色: {user_role_str}")
        
        if not permission_checker.require_role(user_role, allowed_roles):
            raise AuthorizationException(
                f"角色不足，需要以下角色之一: {[r.value for r in allowed_roles]}",
                details={"required_roles": [r.value for r in allowed_roles]}
            )
        return None
    
    return role_dependency


# 导出
__all__ = [
    "Role",
    "Permission",
    "PermissionChecker",
    "permission_checker",
    "ROLE_PERMISSIONS",
    "get_token_from_header",
    "get_current_user",
    "require_permission",
    "require_any_permission",
    "require_role",
]

