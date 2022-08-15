from __future__ import annotations

from pydantic import BaseModel

from app.schemas.booklist import BookListBase
from app.schemas.users.huey_attributes import HueyAttributes
from app.schemas.users.user import UserDetail
from app.schemas.users.user_identity import UserBrief, UserIdentity


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
