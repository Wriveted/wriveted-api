from typing import Optional, Any

from pydantic import BaseModel


class AuthorBrief(BaseModel):
    id: str
    first_name: str
    last_name: str

    class Config:
        orm_mode = True


class AuthorDetail(AuthorBrief):
    info: Optional[Any]
    book_count: int


class AuthorCreateIn(BaseModel):
    first_name: str
    last_name: str

    info: Optional[Any]
