from typing import Optional, Any, List

from pydantic import BaseModel, AnyHttpUrl

from app.schemas.author import AuthorBrief, AuthorCreateIn
from app.schemas.illustrator import IllustratorBrief, IllustratorCreateIn

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

    title: str

    ISBN: str

    cover_url: Optional[AnyHttpUrl]

    info: Optional[EditionInfo]

    authors: List[AuthorCreateIn]
    illustrators: List[IllustratorCreateIn]
