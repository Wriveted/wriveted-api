from typing import List, Literal, Optional

from pydantic import BaseModel, validator

from app.models.work import WorkType
from app.schemas.author import AuthorBrief, AuthorCreateIn
from app.schemas.edition import EditionBrief, Genre
from app.schemas.labelset import (
    CharacterKey,
    GenreKey,
    LabelSetBasic,
    LabelSetCreateIn,
    LabelSetDetail,
    WritingStyleKey,
)
from app.schemas.recommendations import HueKeys, ReadingAbilityKey


class WorkInfo(BaseModel):
    genres: list[Genre]
    other: dict

    @validator("genres", pre=True)
    def genres_not_none(cls, v):
        return v or []


class WorkBrief(BaseModel):
    id: str
    type: Optional[WorkType]

    leading_article: str | None
    title: str
    subtitle: str | None

    authors: List[AuthorBrief]

    class Config:
        orm_mode = True


class WorkEnriched(WorkBrief):
    labelset: LabelSetBasic | None
    cover_url: str | None


class WorkDetail(WorkBrief):
    editions: List[EditionBrief]
    labelset: Optional[LabelSetDetail]
    info: Optional[WorkInfo]


class WorkCreateIn(BaseModel):
    type: WorkType

    leading_article: Optional[str]
    title: str
    subtitle: Optional[str]

    authors: List[AuthorCreateIn]

    series_name: Optional[str]
    series_number: Optional[int]

    info: Optional[dict]


class WorkCreateWithEditionsIn(BaseModel):
    type: WorkType = WorkType.BOOK
    leading_article: Optional[str]
    title: str
    subtitle: Optional[str]
    authors: List[AuthorCreateIn | int]
    editions: list[str]
    info: Optional[dict]


class WorkUpdateIn(BaseModel):
    leading_article: str | None
    title: str | None
    subtitle: str | None

    labelset: LabelSetCreateIn | None
