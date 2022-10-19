from typing import Any, Optional

from pydantic import BaseModel


class ContributorBase(BaseModel):
    first_name: str | None
    last_name: str


class AuthorBrief(ContributorBase):
    id: int

    class Config:
        orm_mode = True


class AuthorDetail(AuthorBrief):
    info: Optional[Any]
    book_count: int


class AuthorCreateIn(ContributorBase):
    info: Optional[Any]
