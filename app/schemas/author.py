from typing import Optional, Any

from pydantic import BaseModel


class AuthorBrief(BaseModel):
    id: str
    full_name: str

    class Config:
        orm_mode = True


class AuthorDetail(AuthorBrief):
    info: Optional[Any]
    book_count: int


class AuthorCreateIn(BaseModel):

    # Used for sorting
    last_name: str

    # How the author appears. E.g. "J.K. Rowling"
    full_name: str

    info: Optional[Any]
