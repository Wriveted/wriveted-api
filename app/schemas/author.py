from typing import Annotated, Any, Optional

from pydantic import BaseModel, BeforeValidator, ConfigDict


class ContributorBase(BaseModel):
    first_name: str | None = None
    last_name: str


class AuthorBrief(ContributorBase):
    id: Annotated[str, BeforeValidator(str)]
    model_config = ConfigDict(from_attributes=True)


class AuthorDetail(AuthorBrief):
    info: Optional[Any] = None
    book_count: int


class AuthorCreateIn(ContributorBase):
    info: Optional[Any] = None
