import enum
from base64 import b64decode
from binascii import Error as BinasciiError
from datetime import datetime
from io import BytesIO
from typing import Optional

from PIL import Image
from pydantic import UUID4, BaseModel, Field, validator
from structlog import get_logger

from app.models.booklist import ListType
from app.schemas.edition import EditionBrief
from app.schemas.pagination import PaginatedResponse
from app.schemas.school import SchoolWrivetedIdentity
from app.schemas.users.user_identity import UserIdentity
from app.schemas.work import WorkBrief

logger = get_logger()


class BookFeedbackChoice(str, enum.Enum):
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
    work: WorkBrief

    class Config:
        orm_mode = True


class BookListItemEnriched(BookListItemDetail):
    edition: EditionBrief


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


class BookListOptionalInfoCreateIn(BookListOptionalInfo):
    image_url: str | None

    @validator("image_url", pre=True)
    def _validate_image_url(cls, v, values: dict):
        if not v:
            return

        logger.info(f"Validating image_url `{v[0:100]}...`")

        # base64 image string validity
        try:
            # remove the metadata from the base64 string before decoding
            raw_image_bytes = b64decode(v.split(",")[1])
            img = Image.open(BytesIO(raw_image_bytes))
        except (BinasciiError, IOError) as e:
            raise ValueError(
                "image_url must be a valid base64 image string, properly formed"
            )

        # image filesize
        if len(raw_image_bytes) > 512_000:
            raise ValueError("Maximum image_url size is 500kb")

        # image formats
        if img.format.lower() not in ["jpg", "jpeg", "png"]:
            raise ValueError("image_url must be either `jpg`, `jpeg`, or `png` format")

        # image dimensions
        width, height = img.size
        if (width < 100) or (height < 100) or (width > 2000) or (height > 2000):
            raise ValueError(
                "Minimum image_url dimensions are 100x100 and maximum dimensions are 2000x2000"
            )

        # we now have a valid base64 string that claims to be an image
        return v


class BookListCreateIn(BaseModel):
    name: str
    type: ListType

    school_id: Optional[str]
    user_id: Optional[str]

    info: Optional[BookListOptionalInfoCreateIn] = None
    items: Optional[list[BookListItemCreateIn]]


class ItemUpdateType(str, enum.Enum):
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
    info: Optional[BookListOptionalInfoCreateIn] = None
    items: Optional[list[BookListItemUpdateIn]]


class BookListBrief(BookListBase):
    created_at: datetime
    updated_at: datetime
    user: Optional[UserIdentity]
    school: Optional[SchoolWrivetedIdentity]
    info: Optional[BookListOptionalInfo]


class BookListsResponse(PaginatedResponse):
    data: list[BookListBrief]


class BookListDetail(PaginatedResponse, BookListBrief):
    data: list[BookListItemDetail]


class BookListDetailEnriched(BookListDetail):
    data: list[BookListItemEnriched]
