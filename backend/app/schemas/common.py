"""
通用 Schema 定义
"""
from typing import TypeVar, Generic, Optional, Any
from pydantic import BaseModel


DataT = TypeVar("DataT")


class ResponseModel(BaseModel, Generic[DataT]):
    """统一响应模型"""
    success: bool = True
    message: str = "操作成功"
    data: Optional[DataT] = None


class PaginationParams(BaseModel):
    """分页参数"""
    page: int = 1
    page_size: int = 20
    
    @property
    def skip(self) -> int:
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        return self.page_size


class PaginatedResponse(BaseModel, Generic[DataT]):
    """分页响应模型"""
    items: list[DataT]
    total: int
    page: int
    page_size: int
    total_pages: int
    
    @classmethod
    def create(
        cls,
        items: list[DataT],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedResponse[DataT]":
        """创建分页响应"""
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size,
        )

