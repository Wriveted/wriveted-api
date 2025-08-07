from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class Pagination(BaseModel):
    skip: int = Field(0, description="Skipped this many items")
    limit: int = Field(100, description="Maximum number of items to return")
    total: Optional[int] = Field(None, description="Total number of items (if known)")
    page: int = Field(0, description="Current page number (calculated from skip/limit)")

    def __init__(self, **data):
        super().__init__(**data)
        # Calculate page number from skip and limit
        if self.limit > 0:
            self.page = (self.skip // self.limit) + 1
        else:
            self.page = 1


class PaginatedResponse(BaseModel, Generic[DataT]):
    data: List[DataT]
    pagination: Optional[Pagination]
