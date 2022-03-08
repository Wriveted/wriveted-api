from typing import Optional, List
from pydantic import BaseModel
from app.models.work import WorkType
from app.schemas.author import AuthorBrief, AuthorCreateIn
from app.schemas.edition import EditionBrief

class WorkBrief(BaseModel):
    id: str
    type: WorkType

    title: str
    authors: List[AuthorBrief]

    class Config:
        orm_mode = True


class WorkDetail(WorkBrief):
    editions: List[EditionBrief]

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