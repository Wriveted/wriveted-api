import enum
from datetime import datetime
from typing import Optional, Any
from uuid import UUID

from pydantic import BaseModel, Field
from app.models.booklist import ListType
from app.schemas.pagination import PaginatedResponse
from app.schemas.school import SchoolBrief
from app.schemas.user import UserBrief
from app.schemas.work import WorkBrief


class BookListItemInfo(BaseModel):
    edition: Optional[str] = Field(None, description="ISBN")
    note: Optional[str] = Field(None, description="Note from the booklist creator")


class BookListItemBase(BaseModel):
    order_id: int
    work_id: str
    info: Optional[BookListItemInfo] = None


class BookListItemDetail(BookListItemBase):
    # id: UUID
    work: WorkBrief

    class Config:
        orm_mode = True


class BookListItemCreateIn(BookListItemBase):
    pass


class BookListBase(BaseModel):
    name: str
    type: ListType


class BookListOptionalInfo(BaseModel):
    description: Optional[str]


class BookListCreateIn(BookListBase):
    info: Optional[BookListOptionalInfo] = None
    items: Optional[list[BookListItemCreateIn]]


class ItemUpdateType(str, enum.Enum):
    ADD = "add"
    REMOVE = "remove"
    UPDATE = "update"


class BookListItemUpdateIn(BaseModel):
    action: ItemUpdateType
    work_id: str

    order_id: Optional[int]
    info: Optional[BookListItemInfo] = None


class BookListUpdateIn(BookListBase):
    name: Optional[str]
    type: Optional[ListType]
    info: Optional[BookListOptionalInfo] = None
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
    info: Optional[BookListOptionalInfo]
    data: list[BookListItemDetail]
