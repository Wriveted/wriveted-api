import enum
from typing import List, Optional, Any

from pydantic import BaseModel

from app.schemas.edition import EditionBrief, EditionCreateIn
from app.schemas.work import WorkBrief


class CollectionItemBrief(BaseModel):

    work: WorkBrief
    edition: EditionBrief

    work_id: str
    edition_id: str

    info: Optional[Any]

    class Config:
        orm_mode = True


class CollectionUpdateType(str, enum.Enum):
    ADD = "add"
    REMOVE = "remove"
    UPDATE = "update"


class CollectionUpdate(BaseModel):
    ISBN: str

    action: CollectionUpdateType
    edition_info: Optional[EditionCreateIn]

    class Config:
        orm_mode = True

