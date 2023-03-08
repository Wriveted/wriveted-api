import enum
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, Field, conint, root_validator, validator
from structlog import get_logger

from app.models.collection_item_activity import CollectionItemReadStatus
from app.schemas import validate_image_url_or_base64_string
from app.schemas.edition import EditionBrief
from app.schemas.pagination import PaginatedResponse
from app.schemas.work import WorkBrief

logger = get_logger()


class CollectionBrief(BaseModel):
    id: UUID
    name: str
    book_count: int
    school_id: UUID | None
    user_id: UUID | None
    updated_at: datetime

    class Config:
        orm_mode = True


class CollectionInfo(BaseModel):
    """
    Count editions in each state in a collection.

    Note this doesn't count additional copies of the same book.
    """

    total_editions: int = Field(
        ..., description="Count of unique editions in this collection"
    )

    hydrated: int = Field(
        ...,
        description="Count of unique editions for which Wriveted has basic metadata",
    )
    hydrated_and_labeled: int = Field(
        ..., description="Count of unique editions for which Wriveted has labelled"
    )
    recommendable: int = Field(
        ..., description="Count of unique editions labelled and marked as recommendable"
    )


class CollectionItemFeedback(BaseModel):
    """
    Feedback about a collection item.
    This is also used to update the feedback for a collection item.
    """

    emojis: list[str] | None
    descriptor: str | None


class CollectionItemInfo(BaseModel):
    cover_image: AnyHttpUrl | None
    title: str | None
    author: str | None

    feedback: CollectionItemFeedback | None

    other: dict[str, Any] | None


class CollectionItemInfoCreateIn(CollectionItemInfo):
    cover_image: str | None

    _validate_cover_image = validator("cover_image", pre=True, allow_reuse=True)(
        validate_image_url_or_base64_string(field_name="cover_image")
    )

    class Config:
        max_anystr_length = (
            2**19
        ) * 1.5  # Max filesize is 500kb, but base64 strings are at least 4/3 the size

        validate_assignment = True


class CoverImageUpdateIn(CollectionItemInfoCreateIn):
    collection_id: UUID | None
    edition_isbn: str


class CollectionItemBase(BaseModel):
    edition_isbn: str | None
    info: CollectionItemInfoCreateIn | None
    copies_total: Optional[conint(ge=0)] = None
    copies_available: Optional[conint(ge=0)] = None


class CollectionItemCreateIn(CollectionItemBase):
    pass


class CollectionItemAndStatusCreateIn(CollectionItemCreateIn):
    read_status: CollectionItemReadStatus | None
    reader_id: UUID | None

    @root_validator(pre=True)
    def _validate_logic(cls, values: dict):
        if not values:
            return

        # if providing one, must provide both
        if (
            values.get("read_status")
            and not values.get("reader_id")
            or (values.get("reader_id") and not values.get("read_status"))
        ):
            raise ValueError(
                "Must provide reader_id when providing read_status, and vice versa"
            )

        return values


class CollectionCreateIn(BaseModel):
    name: str

    school_id: UUID | None
    user_id: UUID | None

    info: dict[str, Any] | None
    items: list[CollectionItemCreateIn] | None

    @root_validator(pre=True)
    def _validate_relationships(cls, values: dict):
        school_id = values.get("school_id")
        user_id = values.get("user_id")
        if not school_id and not user_id:
            raise ValueError("Must provide either school_id or user_id")
        if school_id and user_id:
            raise ValueError("Must provide only one of school_id or user_id")
        return values


class CollectionItemDetail(BaseModel):
    id: int
    work: Optional[WorkBrief]
    edition: EditionBrief | None

    copies_total: Optional[conint(ge=0)] = None
    copies_available: Optional[conint(ge=0)] = None

    info: CollectionItemInfo | None

    class Config:
        orm_mode = True


class CollectionItemsResponse(PaginatedResponse):
    data: list[CollectionItemDetail]


class CollectionUpdateType(str, enum.Enum):
    ADD = "add"
    REMOVE = "remove"
    UPDATE = "update"


class CollectionItemUpdate(CollectionItemCreateIn):
    action: CollectionUpdateType = CollectionUpdateType.ADD
    id: int | None = Field(
        None,
        description="Item id or edition_isbn required if action is `update` or `remove`",
    )

    class Config:
        orm_mode = True


class CollectionUpdateIn(BaseModel):
    name: str | None
    info: dict[str, Any] | None


class CollectionAndItemsUpdateIn(CollectionUpdateIn):
    items: list[CollectionItemUpdate] | None


class CollectionUpdateSummaryResponse(BaseModel):
    msg: str
    collection_size: int


class CollectionItemActivityBase(BaseModel):
    collection_item_id: int
    reader_id: UUID
    status: CollectionItemReadStatus

    class Config:
        orm_mode = True


class CollectionItemActivityBrief(CollectionItemActivityBase):
    timestamp: datetime
