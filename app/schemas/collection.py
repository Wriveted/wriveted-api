import enum
from typing import Any, Optional

from pydantic import BaseModel, Field, conint

from app.schemas.edition import EditionBrief
from app.schemas.work import WorkBrief


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


class CollectionItemBase(BaseModel):
    isbn: str
    copies_total: Optional[conint(ge=0)] = None
    copies_available: Optional[conint(ge=0)] = None


class CollectionItemIn(CollectionItemBase):
    class Config:
        orm_mode = True


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


class CollectionUpdate(CollectionItemBase):
    action: CollectionUpdateType

    class Config:
        orm_mode = True


class CollectionUpdateSummaryResponse(BaseModel):
    msg: str
    collection_size: int
