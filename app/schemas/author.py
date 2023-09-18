from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class ContributorBase(BaseModel):
    first_name: str | None = None
    last_name: str


class AuthorBrief(ContributorBase):
    id: str
    model_config = ConfigDict(from_attributes=True)


class AuthorDetail(AuthorBrief):
    info: Optional[Any] = None
    book_count: int


class AuthorCreateIn(ContributorBase):
    info: Optional[Any] = None
