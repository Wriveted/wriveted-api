from typing import List, Optional, Any

from pydantic import BaseModel

from app.schemas.edition import EditionBrief
from app.schemas.work import WorkBrief


class CollectionItemBrief(BaseModel):

    work: WorkBrief
    edition: EditionBrief

    work_id: str
    edition_id: str

    info: Optional[Any]

    class Config:
        orm_mode = True


class SchoolCollection(BaseModel):
    id: str
    collection: List[CollectionItemBrief]

    class Config:
        orm_mode = True

