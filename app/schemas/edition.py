from datetime import datetime
from typing import Optional

from pydantic import AnyHttpUrl, BaseModel, validator
from app.schemas import CaseInsensitiveStringEnum, validate_image_url_or_base64_string

from app.schemas.author import AuthorBrief, AuthorCreateIn, ContributorBase
from app.schemas.illustrator import IllustratorBrief, IllustratorCreateIn
from app.schemas.labelset import LabelSetCreateIn
from app.schemas.link import LinkBrief


class Genre(BaseModel):
    class GenreSource(CaseInsensitiveStringEnum):
        BISAC = "BISAC"
        BIC = "BIC"
        THEMA = "THEMA"
        LOCSH = "LOCSH"
        HUMAN = "HUMAN"
        OTHER = "OTHER"

    name: str
    source: GenreSource
    code: str | None


class EditionInfo(BaseModel):
    # nielsen fields
    pages: str | None = None  # PAGNUM
    summary_short: str | None = None  # AUSFSD
    summary_long: str | None = None  # AUSFLD
    genres: list[Genre] = []  # BISACT/C{n}, BIC2ST/C{n}, THEMAST/C{n}, LOCSH{n}
    bic_qualifiers: list[str] = []  # BIC2QC{n}
    thema_qualifiers: list[str] = []  # THEMAQC{n}
    keywords: str | None = None  # KEYWORDS (comes as a delimited string, not a list)
    prodct: str | None = None  # PRODCT
    prodcc: str | None = None  # PRODCC
    cbmctext: str | None = None  # CBMCTEXT
    cbmccode: str | None = None  # CBMCCODE
    interest_age: str | None = None  # IA
    reading_age: str | None = None  # RA
    country: str | None = None  # COP
    medium_tags: list[str] = []  # PFCT, PCTCT{n}
    image_flag: bool | None  # IMAGFLAG

    links: list[LinkBrief] = []
    other: dict | None = None


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

    work_id: int | None

    leading_article: Optional[str]
    title: Optional[str]
    subtitle: Optional[str]

    series_name: Optional[str]
    series_number: Optional[int]

    authors: Optional[list[AuthorCreateIn]]
    illustrators: Optional[list[IllustratorCreateIn]]

    cover_url: str | None
    _validate_cover_url = validator("cover_url", allow_reuse=True)(
        lambda v: validate_image_url_or_base64_string(v, field_name="cover_url")
    )

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

    cover_url: str | None
    _validate_cover_url = validator("cover_url", pre=True, allow_reuse=True)(
        lambda v: validate_image_url_or_base64_string(v, field_name="cover_url")
    )

    work_id: int | None

    info: EditionInfo | None

    hydrated_at: datetime | None


class KnownAndTaggedEditionCounts(BaseModel):
    num_provided: int
    num_valid: int
    num_known: int
    num_fully_tagged: int
