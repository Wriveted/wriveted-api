from typing import Optional, Any, List

from pydantic import BaseModel

from app.models.work import WorkType
from app.schemas.author import AuthorBrief, AuthorCreateIn
from app.schemas.edition import EditionBrief


class WorkBrief(BaseModel):
    id: str
    type: WorkType

    title: str
    authors: List[AuthorBrief]

    class Config:
        orm_mode = True


class WorkDetail(WorkBrief):

    info: Optional[Any]
    editions: List[EditionBrief]

    class Config:
        orm_mode = True


class WorkCreateIn(BaseModel):
    type: WorkType
    title: str
    authors: List[AuthorCreateIn]
    info: Optional[Any]

    series_title: Optional[str]
