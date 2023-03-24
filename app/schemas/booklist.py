from datetime import datetime
from typing import Optional

from pydantic import UUID4, BaseModel, Field, validator

from app.models.booklist import ListSharingType, ListType
from app.schemas import CaseInsensitiveStringEnum, validate_image_url_or_base64_string
from app.schemas.edition import EditionDetail
from app.schemas.pagination import PaginatedResponse
from app.schemas.school import SchoolWrivetedIdentity
from app.schemas.users.user_identity import UserIdentity
from app.schemas.work import WorkEnriched


class BookFeedbackChoice(CaseInsensitiveStringEnum):
    GOOD = "GOOD"
    BAD = "BAD"
    READ_GOOD = "READ_GOOD"
    READ_BAD = "READ_BAD"


class BookListItemInfo(BaseModel):
    edition: Optional[str] = Field(None, description="ISBN")
    note: Optional[str] = Field(None, description="Note from the booklist creator")
    feedback: BookFeedbackChoice | None


class BookListItemBase(BaseModel):
    order_id: int
    work_id: int
    info: Optional[BookListItemInfo] = None


class BookListItemDetail(BookListItemBase):
    # id: UUID
    work: WorkEnriched

    class Config:
        orm_mode = True


class BookListItemEnriched(BookListItemDetail):
    edition: EditionDetail


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
    image_url: Optional[str]
    subheading: Optional[str]
    colour: Optional[str]


class BookListOptionalInfoCreateIn(BookListOptionalInfo):
    image_url: str | None

    _validate_image_url = validator("image_url", allow_reuse=True)(
        lambda v: validate_image_url_or_base64_string(v, field_name="image_url")
    )


class BookListCreateIn(BaseModel):
    name: str
    type: ListType
    slug: str | None
    sharing: ListSharingType | None

    school_id: str | None
    user_id: str | None

    info: BookListOptionalInfo | None = None
    items: list[BookListItemCreateIn] | None


class ItemUpdateType(CaseInsensitiveStringEnum):
    ADD = "add"
    REMOVE = "remove"
    UPDATE = "update"


class BookListItemUpdateIn(BaseModel):
    action: ItemUpdateType
    work_id: int
    order_id: Optional[int]
    info: Optional[BookListItemInfo] = None


class BookListUpdateIn(BaseModel):
    name: Optional[str]
    type: Optional[ListType]
    sharing: Optional[ListSharingType]
    slug: Optional[str]
    info: Optional[BookListOptionalInfo] = None
    items: Optional[list[BookListItemUpdateIn]]


class BookListBrief(BookListBase):
    created_at: datetime
    updated_at: datetime
    user: Optional[UserIdentity]
    school: Optional[SchoolWrivetedIdentity]
    sharing: Optional[ListSharingType]
    slug: Optional[str]
    info: Optional[BookListOptionalInfo]


class BookListsResponse(PaginatedResponse):
    data: list[BookListBrief]


class BookListDetail(PaginatedResponse, BookListBrief):
    data: list[BookListItemDetail]


class BookListDetailEnriched(BookListDetail):
    data: list[BookListItemEnriched]
