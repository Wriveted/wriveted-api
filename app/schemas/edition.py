from pydantic import BaseModel, AnyHttpUrl
from sqlalchemy import JSON
from app.schemas.author import AuthorBrief, AuthorCreateIn
from app.schemas.genre import Genre
from app.schemas.illustrator import IllustratorBrief, IllustratorCreateIn
from app.schemas.labelset import LabelSetCreateIn

class EditionInfo(BaseModel):
    pages:            int | None
    summary_short:    str | None
    summary_long:     str | None

    genres:           list[Genre]
    bic_qualifiers:   list[str]
    thema_qualifiers: list[str]
    keywords:         str | None # comes as a delimited string, not a list
    prodct:           str | None
    cbmctext:         str | None
    interest_age:     str | None
    reading_age:      str | None

    country:          str | None

    medium_tags:      list[str]
    image_flag:       bool
    
    other:            dict | None


class EditionBrief(BaseModel):
    title:   str | None
    work_id: str | None
    isbn:    str

    class Config:
        orm_mode = True


class EditionDetail(BaseModel):
    work_id:        int | None
    title:          str | None # should be the edition title with a fallback to the Works title
    series_name:    str | None
    series_number:  int | None

    authors:        list[AuthorBrief]
    illustrators:   list[IllustratorBrief]

    cover_url:      AnyHttpUrl | None
    date_published: str | None
    info:           EditionInfo | None

    class Config:
        orm_mode = True


class EditionCreateIn(BaseModel):
    isbn:          str
    other_isbns:   list[str]

    title:         str | None
    series_name:   str | None
    series_number: int | None

    authors:       list[AuthorCreateIn]
    illustrators:  list[IllustratorCreateIn]

    cover_url:     AnyHttpUrl | None

    labelset:      LabelSetCreateIn | None
    info:          EditionInfo | None


class KnownAndTaggedEditionCounts(BaseModel):
    num_provided:     int
    num_valid:        int
    num_known:        int
    num_fully_tagged: int