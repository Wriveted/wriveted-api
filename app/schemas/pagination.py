from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field
from pydantic.generics import GenericModel

DataT = TypeVar("DataT")


class Pagination(BaseModel):
    skip: int = Field(0, description="Skipped this many items")
    limit: int = Field(100, description="Maximum number of items to return")
    total: Optional[int] = Field(None, description="Total number of items (if known)")


class PaginatedResponse(GenericModel, Generic[DataT]):
    data: List[DataT]
    pagination: Optional[Pagination]
