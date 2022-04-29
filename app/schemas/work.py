from typing import List, Optional

from pydantic import BaseModel

from app.models.work import WorkType
from app.schemas.author import AuthorBrief, AuthorCreateIn
from app.schemas.edition import EditionBrief, Genre
from app.schemas.labelset import LabelSetDetail


class WorkInfo(BaseModel):
    genres: list[Genre]
    other: dict


class WorkBrief(BaseModel):
    id: str
    type: Optional[WorkType]

    title: str
    authors: List[AuthorBrief]

    class Config:
        orm_mode = True


class WorkDetail(WorkBrief):
    editions: List[EditionBrief]
    labelset: Optional[LabelSetDetail]
    info: Optional[WorkInfo]

    class Config:
        orm_mode = True


class WorkCreateIn(BaseModel):
    type: WorkType

    leading_article: Optional[str]
    title: str
    subtitle: Optional[str]

    authors: List[AuthorCreateIn]

    series_name: Optional[str]
    series_number: Optional[int]

    info: Optional[dict]
