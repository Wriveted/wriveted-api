import datetime
import enum
from typing import Optional

from pydantic import BaseModel, Field
from typing import Generic, TypeVar, Optional, List

from pydantic import BaseModel
from pydantic.generics import GenericModel

DataT = TypeVar("DataT")


class Pagination(BaseModel):
    skip: int = Field(0, description="Skipped this many items")
    limit: int = Field(100, description="Maximum number of items to return")


class PaginatedResponse(GenericModel, Generic[DataT]):
    data: List[DataT]
    pagination: Optional[Pagination]
