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

    copies_available: Optional[conint(ge=0)]
    copies_on_loan: Optional[conint(ge=0)]

    class Config:
        orm_mode = True


class CollectionItemIn(EditionCreateIn):
    copies_available: Optional[conint(ge=0)] = None
    copies_on_loan: Optional[conint(ge=0)] = None


class CollectionUpdateType(str, enum.Enum):
    ADD = "add"
    REMOVE = "remove"
    UPDATE = "update"


class CollectionUpdate(BaseModel):
    ISBN: str

    action: CollectionUpdateType
    edition_info: Optional[EditionCreateIn]

    copies_available: Optional[conint(ge=0)]
    copies_on_loan: Optional[conint(ge=0)]

    class Config:
        orm_mode = True

