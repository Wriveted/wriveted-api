from typing import Optional, Any, List

from pydantic import BaseModel

from app.models.work import WorkType
from app.schemas.author import AuthorBrief, AuthorCreateIn
from app.schemas.edition import EditionBrief

class WorkInfo:
    genre: Optional[list[str]]
    characters: Optional[list[str]]
    summary: Optional[str]
    prc_reading_level: Optional[str]
    version: Optional[str]


class WorkBrief(BaseModel):
    id: str
    type: WorkType

    title: str
    authors: List[AuthorBrief]

    class Config:
        orm_mode = True


class WorkDetail(WorkBrief):
    info: Optional[WorkInfo]
    editions: List[EditionBrief]

    class Config:
        orm_mode = True


class SeriesCreateIn(BaseModel):
    title: str
    info: Optional[Any]


class WorkCreateIn(BaseModel):
    type: WorkType
    title: str
    authors: List[AuthorCreateIn]
    info: Optional[WorkInfo]

    series: Optional[SeriesCreateIn]