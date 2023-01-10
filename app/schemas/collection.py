import enum
from base64 import b64decode
from binascii import Error as BinasciiError
from io import BytesIO
from typing import Any, Optional
from uuid import UUID

from PIL import Image
from pydantic import AnyHttpUrl, BaseModel, Field, conint, root_validator, validator
from structlog import get_logger

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
        if not v:
            return

        logger.info(f"Validating cover_image `{v[0:100]}...`")

        # base64 image string validity
        try:
            # remove the metadata from the base64 string before decoding
            raw_image_bytes = b64decode(v.split(",")[1])
            img = Image.open(BytesIO(raw_image_bytes))
        except (BinasciiError, IOError) as e:
            raise ValueError(
                "cover_image must be a valid base64 image string, properly formed"
            )

        # image filesize
        if len(raw_image_bytes) > 512_000:
            raise ValueError("Maximum cover_image size is 500kb")

        # image formats
        if img.format.lower() not in ["jpg", "jpeg", "png"]:
            raise ValueError(
                "cover_image must be either `jpg`, `jpeg`, or `png` format"
            )

        # image dimensions
        width, height = img.size
        if (width < 100) or (height < 100) or (width > 1000) or (height > 1000):
            raise ValueError(
                "Minimum cover_image dimensions are 100x100 and maximum dimensions are 1000x1000"
            )

        # we now have a valid base64 string that claims to be an image
        return v

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

    class Config:
        orm_mode = True


class CollectionItemInnerCreateIn(CollectionItemBase):
    collection_id: UUID
    info: CollectionItemInfo | None


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
