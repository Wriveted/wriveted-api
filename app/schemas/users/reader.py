from __future__ import annotations

from pydantic import BaseModel, validator, root_validator
from sqlalchemy.orm.dynamic import AppenderQuery

from app.schemas.booklist import BookListBase
from app.schemas.users.huey_attributes import HueyAttributes
from app.schemas.users.user import UserDetail
from app.schemas.users.user_identity import UserBrief, UserIdentity


class ReadingPath(BaseModel):
    read_now: BookListBase | None
    read_next: BookListBase | None


class ReaderBase(BaseModel):
    first_name: str | None
    last_name_initial: str | None


class ReaderIdentity(ReaderBase, UserIdentity):
    pass


class ReaderBrief(ReaderBase, UserBrief):
    huey_attributes: HueyAttributes
    parent: UserIdentity | None


class ReaderDetail(ReaderBrief, UserDetail):
    booklists: list[BookListBase]
    reading_path: ReadingPath = None

    @validator("reading_path", pre=True, always=True)
    def grab_pathway_lists(cls, v, values):
        lists = values["booklists"]
        output = {"read_now": None, "read_next": None}
        # get the first booklist matching each required name (with null safeties)
        output["read_now"] = next(
            iter(filter(lambda list: list.name == "Books To Read Now", lists) or []),
            None,
        )
        output["read_next"] = next(
            iter(filter(lambda list: list.name == "Books To Read Next", lists) or []),
            None,
        )
        return output

    @validator("booklists", pre=True)
    def limit_booklists(cls, v):
        return v[:5] if isinstance(v, (AppenderQuery, list)) else v
