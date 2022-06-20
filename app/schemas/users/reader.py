from __future__ import annotations

from pydantic import BaseModel

from app.schemas.booklist import BookListBase
from app.schemas.users.huey_attributes import HueyAttributes
from app.schemas.users.user_identity import UserBrief, UserIdentity


class ReaderBase(BaseModel):
    username: str
    first_name: str
    last_name_initial: str


class ReaderIdentity(ReaderBase, UserIdentity):
    pass


class ReaderBrief(ReaderBase, UserBrief):
    huey_attributes: HueyAttributes
    parent: UserIdentity | None


class ReaderDetail(ReaderBrief):
    booklists: list[BookListBase]
