from typing import List, Optional

from pydantic import BaseModel, validator

from app.models.work import WorkType
from app.schemas.author import AuthorBrief, AuthorCreateIn
from app.schemas.edition import EditionBrief, Genre
from app.schemas.labelset import LabelSetCreateIn, LabelSetDetail


class WorkInfo(BaseModel):
    genres: list[Genre]
    other: dict

    @validator("genres", pre=True)
    def genres_not_none(cls, v):
        return v or []


class WorkBrief(BaseModel):
    id: int
    type: Optional[WorkType]

    leading_article: str | None
    title: str
    subtitle: str | None

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


class WorkUpdateIn(BaseModel):
    leading_article: str | None
    title: str | None
    subtitle: str | None

    labelset: LabelSetCreateIn | None
