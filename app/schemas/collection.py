import enum
from typing import Optional, Any
from pydantic import BaseModel, conint
from app.schemas.edition import EditionBrief
from app.schemas.work import WorkBrief

class CollectionItemIn(BaseModel):
    isbn: str
    copies_total: Optional[conint(ge=0)] = None
    copies_available: Optional[conint(ge=0)] = None

    class Config:
        orm_mode = True

    
class CollectionItemBrief(CollectionItemIn):

    work: WorkBrief
    edition: EditionBrief

    work_id: str
    edition_id: str

    info: Optional[Any]


class CollectionUpdateType(str, enum.Enum):
    ADD = "add"
    REMOVE = "remove"
    UPDATE = "update"


class CollectionUpdate(BaseModel):
    isbn: str

    action: CollectionUpdateType

    copies_total: Optional[conint(ge=0)]
    copies_available: Optional[conint(ge=0)]

    class Config:
        orm_mode = True
