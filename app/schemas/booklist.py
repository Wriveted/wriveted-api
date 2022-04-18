import enum
from datetime import datetime
from typing import Optional, Any
from uuid import UUID

from pydantic import BaseModel
from app.models.booklist import ListType
from app.schemas.pagination import PaginatedResponse
from app.schemas.school import SchoolBrief
from app.schemas.user import UserBrief
from app.schemas.work import WorkBrief


class BookListBase(BaseModel):
    name: str
    type: ListType


class BookListItemBase(BaseModel):
    order_id: int
    work_id: str
    info: Optional[dict[str, Any]] = None


class BookListItemDetail(BookListItemBase):
    # id: UUID
    work: WorkBrief

    class Config:
        orm_mode = True


class BookListItemCreateIn(BookListItemBase):
    pass


class BookListCreateIn(BookListBase):
    info: Optional[dict[str, Any]] = None
    items: Optional[list[BookListItemCreateIn]]


class ItemUpdateType(str, enum.Enum):
    ADD = "add"
    REMOVE = "remove"
    UPDATE = "update"


class BookListItemUpdateIn(BaseModel):
    action: ItemUpdateType
    work_id: str

    order_id: Optional[int]
    info: Optional[dict[str, Any]] = None


class BookListUpdateIn(BookListBase):
    name: Optional[str]
    type: Optional[ListType]
    info: Optional[dict[str, Any]] = None
    items: Optional[list[BookListItemUpdateIn]]


class BookListBrief(BookListBase):
    id: UUID
    created_at: datetime
    book_count: int
    user: Optional[UserBrief]
    school: Optional[SchoolBrief]

    class Config:
        orm_mode = True


class BookListsResponse(PaginatedResponse):
    data: list[BookListBrief]


class BookListDetail(PaginatedResponse, BookListBrief):
    info: Optional[dict[str, Any]]
    data: list[BookListItemDetail]
