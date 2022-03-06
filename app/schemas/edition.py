from typing import Optional
from pydantic import BaseModel, AnyHttpUrl
from app.schemas.author import AuthorBrief, AuthorCreateIn
from app.schemas.genre import Genre
from app.schemas.illustrator import IllustratorBrief, IllustratorCreateIn
from app.schemas.labelset import LabelSetCreateIn

class EditionInfo(BaseModel):
    pages:            Optional[int]
    summary_short:    Optional[str]
    summary_long:     Optional[str]

    genres:           list[Genre]
    bic_qualifiers:   list[str]
    thema_qualifiers: list[str]
    keywords:         Optional[str] # comes as a delimited string, not a list
    prodct:           Optional[str]
    cbmctext:         Optional[str]
    interest_age:     Optional[str]
    reading_age:      Optional[str]

    country:          Optional[str]

    medium_tags:      list[str]
    image_flag:       bool
    
    other:            Optional[dict]


class EditionBrief(BaseModel):
    title:   Optional[str]
    work_id: Optional[str]
    isbn:    str

    class Config:
        orm_mode = True


class EditionDetail(BaseModel):
    work_id:        Optional[int]
    title:          Optional[str] # should be the edition title with a fallback to the Works title
    series_name:    Optional[str]
    series_number:  Optional[int]

    authors:        list[AuthorBrief]
    illustrators:   list[IllustratorBrief]

    cover_url:      Optional[AnyHttpUrl]
    date_published: Optional[str]
    info:           Optional[EditionInfo]

    class Config:
        orm_mode = True


class EditionCreateIn(BaseModel):
    isbn:            str
    other_isbns:     list[str]

    title:           Optional[str]
    leading_article: Optional[str]
    series_name:     Optional[str]
    series_number:   Optional[int]

    authors:         list[AuthorCreateIn]
    illustrators:    list[IllustratorCreateIn]
  
    cover_url:       Optional[AnyHttpUrl]
  
    labelset:        Optional[LabelSetCreateIn]
    info:            Optional[EditionInfo]


class KnownAndTaggedEditionCounts(BaseModel):
    num_provided:     int
    num_valid:        int
    num_known:        int
    num_fully_tagged: int