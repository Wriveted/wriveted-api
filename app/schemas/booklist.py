import enum
from datetime import datetime
from typing import Optional

from pydantic import UUID4, BaseModel, Field

from app.models.booklist import ListType
from app.schemas.edition import EditionDetail
from app.schemas.pagination import PaginatedResponse
from app.schemas.school import SchoolWrivetedIdentity
from app.schemas.users.user_identity import UserIdentity
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


class BookListItemEnriched(BaseModel):
    order_id: int
    edition: EditionDetail
    note: Optional[str] = Field(None, description="Note from the booklist creator")


class BookListItemCreateIn(BookListItemBase):
    order_id: Optional[int]


class BookListBase(BaseModel):
    id: UUID4
    name: str
    type: ListType
    book_count: int | None

    class Config:
        orm_mode = True


class BookListOptionalInfo(BaseModel):
    description: Optional[str]


class BookListCreateIn(BaseModel):
    name: str
    type: ListType

    school_id: Optional[str]
    user_id: Optional[str]

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


class BookListUpdateIn(BaseModel):
    name: Optional[str]
    type: Optional[ListType]
    info: Optional[BookListOptionalInfo] = None
    items: Optional[list[BookListItemUpdateIn]]


class BookListBrief(BookListBase):
    created_at: datetime
    updated_at: datetime
    user: Optional[UserIdentity]
    school: Optional[SchoolWrivetedIdentity]


class BookListsResponse(PaginatedResponse):
    data: list[BookListBrief]


class BookListDetail(PaginatedResponse, BookListBrief):
    info: Optional[BookListOptionalInfo]
    data: list[BookListItemDetail]


class BookListDetailEnriched(BookListDetail):
    data: list[BookListItemEnriched]
