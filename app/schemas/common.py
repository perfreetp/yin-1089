from pydantic import BaseModel, Field
from typing import Generic, TypeVar, Optional, List

T = TypeVar("T")


class PaginationParams(BaseModel):
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页条数")


class PaginationResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class SuccessResponse(BaseModel, Generic[T]):
    code: int = 200
    message: str = "success"
    data: Optional[T] = None


class ErrorResponse(BaseModel):
    code: int
    message: str
    detail: Optional[str] = None
