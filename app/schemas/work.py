from typing import Optional, Any, List, Text
from pydantic import BaseModel
from app.models.work import WorkType
from app.schemas.author import AuthorBrief, AuthorCreateIn
from app.schemas.edition import EditionBrief
from app.schemas.genre import Genre

class WorkInfo(BaseModel):
    short_summary: Optional[Text]
    long_summary: Optional[Text]
    keywords: Optional[str]
    interest_age: Optional[str]
    reading_age: Optional[str]
    genres: Optional[list[Genre]]
    series_title: Optional[str]

    characters: Optional[list[str]]
    prc_reading_level: Optional[str]

    version: Optional[str]
    other: Optional[dict]


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