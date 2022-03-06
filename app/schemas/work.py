from typing import Optional, List
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
    editions: List[EditionBrief]

    class Config:
        orm_mode = True


class SeriesCreateIn(BaseModel):
    title: str


class WorkCreateIn(BaseModel):
    type: WorkType
    title: str
    authors: List[AuthorCreateIn]
    series: Optional[SeriesCreateIn]