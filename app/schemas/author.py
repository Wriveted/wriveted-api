from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, validator


class ContributorBase(BaseModel):
    first_name: str | None = None
    last_name: str

    # TODO[pydantic]: We couldn't refactor the `validator`, please replace it by `field_validator` manually.
    # Check https://docs.pydantic.dev/dev-v2/migration/#changes-to-validators for more information.
    @validator("last_name", pre=True)
    def validate_name(cls, value, values):
        if not value and values.get("first_name"):
            return values.get("first_name")
        else:
            return value


class AuthorBrief(ContributorBase):
    id: str
    model_config = ConfigDict(from_attributes=True)


class AuthorDetail(AuthorBrief):
    info: Optional[Any] = None
    book_count: int


class AuthorCreateIn(ContributorBase):
    info: Optional[Any] = None
