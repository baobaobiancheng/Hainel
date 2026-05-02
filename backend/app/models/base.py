"""
基础模型类
定义所有数据库模型的公共字段和方法
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, DateTime, func
from sqlalchemy.ext.declarative import declared_attr

from app.database.base import Base


class BaseModel(Base):
    """基础模型类，所有模型都继承此类"""
    
    __abstract__ = True
    
    # 主键ID
    id = Column(Integer, primary_key=True, index=True, autoincrement=True, comment="主键ID")
    
    # 创建时间
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        server_default=func.now(),
        nullable=False,
        comment="创建时间",
    )
    
    # 更新时间
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=func.now(),
        server_onupdate=func.now(),
        nullable=False,
        comment="更新时间",
    )
    
    @declared_attr
    def __tablename__(cls):
        """
        自动生成表名
        将类名转换为小写下划线格式
        例如: User -> users, MedicalRecord -> medical_records
        """
        import re
        # 将驼峰命名转换为下划线命名
        name = re.sub(r'(?<!^)(?=[A-Z])', '_', cls.__name__).lower()
        # 如果以复数形式结尾，直接返回；否则添加s
        if name.endswith('s'):
            return name
        return f"{name}s"
    
    def to_dict(self, exclude: Optional[list] = None) -> dict:
        """
        将模型转换为字典
        
        Args:
            exclude: 要排除的字段列表
        
        Returns:
            字典对象
        """
        exclude = exclude or []
        result = {}
        for column in self.__table__.columns:
            if column.name not in exclude:
                value = getattr(self, column.name)
                # 处理datetime对象
                if isinstance(value, datetime):
                    value = value.isoformat()
                result[column.name] = value
        return result
    
    def update_from_dict(self, data: dict, exclude: Optional[list] = None):
        """
        从字典更新模型属性
        
        Args:
            data: 包含更新数据的字典
            exclude: 要排除的字段列表（如id、created_at等）
        """
        exclude = exclude or ['id', 'created_at', 'updated_at']
        for key, value in data.items():
            if key not in exclude and hasattr(self, key):
                setattr(self, key, value)
    
    def __repr__(self) -> str:
        """返回模型的字符串表示"""
        return f"<{self.__class__.__name__}(id={self.id})>"


# 导出
__all__ = ["BaseModel"]

