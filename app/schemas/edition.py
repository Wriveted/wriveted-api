from typing import Optional, Any, List, Text
from pydantic import BaseModel, AnyHttpUrl
from sqlalchemy import JSON
from app.schemas.author import AuthorBrief, AuthorCreateIn
from app.schemas.genre import Genre
from app.schemas.illustrator import IllustratorBrief, IllustratorCreateIn

class WorkInfo(BaseModel):
    short_summary: Optional[str]
    long_summary: Optional[str]
    keywords: Optional[str]
    interest_age: Optional[str]
    reading_age: Optional[str]
    genres: Optional[List[Genre]]
    series_title: Optional[str]

    characters: Optional[List[str]]
    prc_reading_level: Optional[str]

    version: Optional[str]
    other: Optional[dict]


class EditionInfo(BaseModel):
    pages: Optional[int]
    version: Optional[str]
    other: Optional[dict]


class EditionBrief(BaseModel):
    title: str
    work_id: str
    ISBN: str

    class Config:
        orm_mode = True


class EditionDetail(BaseModel):

    # This should be the edition title with a fallback to the Works title
    title: str
    work_id: str
    ISBN: str

    cover_url: Optional[AnyHttpUrl]
    info: Optional[EditionInfo]

    authors: List[AuthorBrief]
    illustrators: List[IllustratorBrief]

    class Config:
        orm_mode = True


class EditionCreateIn(BaseModel):

    work_id: Optional[str]

    # Only required if different from title
    work_title: Optional[str]
    series_title: Optional[str]
    series_number: Optional[str]

    title: str
    ISBN: str
    cover_url: Optional[AnyHttpUrl]

    info: Optional[EditionInfo]

    # we need the workinfo to create 
    work_info: Optional[WorkInfo]

    authors: List[AuthorCreateIn]
    illustrators: List[IllustratorCreateIn]
