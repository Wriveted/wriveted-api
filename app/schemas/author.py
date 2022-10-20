from typing import Any, Optional

from pydantic import BaseModel, validator


class ContributorBase(BaseModel):
    first_name: str | None
    last_name: str

    @validator("last_name", pre=True)
    def validate_name(cls, value, values):
        if not value and values.get("first_name"):
            return values.get("first_name")
        else:
            return value


class AuthorBrief(ContributorBase):
    id: int

    class Config:
        orm_mode = True


class AuthorDetail(AuthorBrief):
    info: Optional[Any]
    book_count: int


class AuthorCreateIn(ContributorBase):
    info: Optional[Any]
