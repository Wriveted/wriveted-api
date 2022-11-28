import enum
from typing import Any, Optional
from uuid import UUID

from base64 import b64encode, b64decode
from binascii import Error as BinasciiError

from pydantic import AnyHttpUrl, BaseModel, Field, conint, root_validator, validator

from app.schemas.edition import EditionBrief
from app.schemas.work import WorkBrief


class CollectionBrief(BaseModel):
    id: UUID
    name: str
    book_count: int
    school_id: UUID | None
    user_id: UUID | None

    class Config:
        orm_mode = True


class CollectionInfo(CollectionBrief):
    """
    Count editions in each state in a collection.

    Note this doesn't count additional copies of the same book.
    """

    total_editions: int = Field(
        ..., description="Count of unique editions in this collection"
    )

    @validator("total_editions", pre=True)
    def _validate_total_editions(cls, v, values: dict):
        return values.get("book_count", 0)

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


class CollectionItemSentiment(BaseModel):
    # Thanks to text-processing.com
    pos: float
    neg: float
    neutral: float
    polar: float


class CollectionItemFeedback(BaseModel):
    """
    Feedback about a collection item.
    This is also used to update the feedback for a collection item.
    """

    emojis: list[str] | None
    descriptor: str | None
    sentiment: CollectionItemSentiment | None


class CollectionItemInfo(BaseModel):
    cover_image: AnyHttpUrl | None
    title: str | None
    author: str | None

    feedback: CollectionItemFeedback | None

    other: dict[str, Any] | None


class CollectionItemInfoCreateIn(CollectionItemInfo):
    cover_image: str | None

    @validator("cover_image", pre=True)
    def _validate_cover_image(cls, v, values: dict):
        # first thing's first
        if v is not None and not v.startswith("data:image"):
            raise ValueError(
                "cover_image must be a valid base64 image string, beginning with 'data:image'"
            )

        # if the string is misformed, decoding will fail
        try:
            decoded = b64decode(v, validate=True)
        except BinasciiError:
            raise ValueError(
                "cover_image must be a valid base64 image string, properly formed"
            )

        # decoding and re-encoding a valid string should be idempotent. any diff indicates invalidity
        if v is not None and not b64encode(decoded) == v:
            raise ValueError("cover_image must be a valid base64 image string")

        # we now have a valid base64 string that claims to be an image
        return v


class CoverImageUpdateIn(CollectionItemInfoCreateIn):
    collection_id: UUID | None
    edition_isbn: str


class CollectionItemBase(BaseModel):
    edition_isbn: str
    info: CollectionItemInfo | None
    copies_total: Optional[conint(ge=0)] = None
    copies_available: Optional[conint(ge=0)] = None

    class Config:
        orm_mode = True


class CollectionItemInnerCreateIn(CollectionItemBase):
    collection_id: UUID


class CollectionCreateIn(BaseModel):
    name: str

    school_id: UUID | None
    user_id: UUID | None

    info: dict[str, Any] | None
    items: list[CollectionItemBase] | None

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
    work: Optional[WorkBrief]
    edition: EditionBrief

    copies_total: Optional[conint(ge=0)] = None
    copies_available: Optional[conint(ge=0)] = None

    info: Optional[Any]

    class Config:
        orm_mode = True


class CollectionUpdateType(str, enum.Enum):
    ADD = "add"
    REMOVE = "remove"
    UPDATE = "update"


class CollectionItemUpdate(CollectionItemBase):
    action: CollectionUpdateType = CollectionUpdateType.ADD

    class Config:
        orm_mode = True


class CollectionUpdateIn(BaseModel):
    name: str | None
    info: CollectionInfo | None = None


class CollectionAndItemsUpdateIn(CollectionUpdateIn):
    items: list[CollectionItemUpdate] | None


class CollectionUpdateSummaryResponse(BaseModel):
    msg: str
    collection_size: int
