from typing import Optional, Any, List, Text
from pydantic import BaseModel
from sqlalchemy import JSON
from app.models.work import WorkType
from app.schemas.author import AuthorBrief, AuthorCreateIn
from app.schemas.edition import EditionBrief, WorkInfo
from app.schemas.genre import Genre

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
    info: Optional[WorkInfo]


class WorkCreateIn(BaseModel):
    type: WorkType
    title: str
    authors: List[AuthorCreateIn]
    info: Optional[WorkInfo]

    series: Optional[SeriesCreateIn]