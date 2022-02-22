import enum
from typing import List, Optional, Any

from pydantic import BaseModel, conint

from app.schemas.edition import EditionBrief, EditionCreateIn
from app.schemas.work import WorkBrief


class CollectionItemBrief(BaseModel):

    work: WorkBrief
    edition: EditionBrief

    work_id: str
    edition_id: str

    info: Optional[Any]

    copies_total: Optional[conint(ge=0)]
    copies_available: Optional[conint(ge=0)]

    class Config:
        orm_mode = True


class CollectionItemIn(EditionCreateIn):
    copies_total: Optional[conint(ge=0)] = None
    copies_available: Optional[conint(ge=0)] = None


class CollectionUpdateType(str, enum.Enum):
    ADD = "add"
    REMOVE = "remove"
    UPDATE = "update"


class CollectionUpdate(BaseModel):
    isbn: str

    action: CollectionUpdateType
    edition_info: Optional[EditionCreateIn]

    copies_total: Optional[conint(ge=0)]
    copies_available: Optional[conint(ge=0)]

    class Config:
        orm_mode = True
