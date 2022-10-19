from enum import Enum
from typing import Optional

from pydantic import AnyHttpUrl, BaseModel, validator
from app.models.illustrator import Illustrator

from app.schemas.author import AuthorBrief, AuthorCreateIn, ContributorBase
from app.schemas.illustrator import IllustratorBrief, IllustratorCreateIn
from app.schemas.labelset import LabelSetCreateIn


class Genre(BaseModel):
    class GenreSource(str, Enum):
        BISAC = "BISAC"
        BIC = "BIC"
        THEMA = "THEMA"
        LOCSH = "LOCSH"
        HUMAN = "HUMAN"
        OTHER = "OTHER"

    name: str
    source: GenreSource


class EditionInfo(BaseModel):
    pages: Optional[int]
    summary_short: Optional[str]
    summary_long: Optional[str]

    genres: Optional[list[Genre]]
    bic_qualifiers: Optional[list[str]]
    thema_qualifiers: Optional[list[str]]
    keywords: Optional[str]  # comes as a delimited string, not a list
    prodct: Optional[str]
    prodcc: Optional[str]
    cbmctext: Optional[str]
    cbmccode: Optional[str]
    interest_age: Optional[str]
    reading_age: Optional[str]

    country: Optional[str]

    medium_tags: Optional[list[str]]
    image_flag: Optional[bool]

    other: Optional[dict]


class EditionBrief(BaseModel):
    leading_article: Optional[str]
    title: Optional[str]
    subtitle: Optional[str]
    cover_url: Optional[AnyHttpUrl]
    work_id: Optional[str]
    isbn: str

    class Config:
        orm_mode = True


class EditionDetail(EditionBrief):
    series_name: Optional[str]
    series_number: Optional[int]

    authors: list[AuthorBrief]
    illustrators: list[IllustratorBrief]

    date_published: Optional[int]
    info: Optional[EditionInfo]

    @validator("authors", "illustrators", pre=True)
    def contributors_not_none(cls, v):
        return v or []


class EditionCreateIn(BaseModel):
    isbn: str
    other_isbns: Optional[list[str]]

    leading_article: Optional[str]
    title: Optional[str]
    subtitle: Optional[str]

    series_name: Optional[str]
    series_number: Optional[int]

    authors: Optional[list[AuthorCreateIn]]
    illustrators: Optional[list[IllustratorCreateIn]]

    cover_url: Optional[AnyHttpUrl]
    date_published: Optional[int]

    labelset: Optional[LabelSetCreateIn]
    info: Optional[EditionInfo]

    hydrated: bool = False


class EditionUpdateIn(BaseModel):
    leading_article: str | None
    edition_title: str | None
    edition_subtitle: str | None

    date_published: str | None

    illustrators: list[ContributorBase | int] | None

    work_id: int | None

    info: EditionInfo | None


class KnownAndTaggedEditionCounts(BaseModel):
    num_provided: int
    num_valid: int
    num_known: int
    num_fully_tagged: int
