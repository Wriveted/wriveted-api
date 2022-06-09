from __future__ import annotations

from pydantic import BaseModel

from app.schemas.booklist import BookListBase
from app.schemas.users.reading_preferences import ReadingPreferences
from app.schemas.users.user_identity import UserBrief, UserIdentity


class ReaderBase(BaseModel):
    username: str
    first_name: str
    last_name_initial: str


class ReaderIdentity(ReaderBase, UserIdentity):
    pass


class ReaderBrief(ReaderBase, UserBrief):
    reading_preferences: ReadingPreferences
    parent: UserIdentity | None


class ReaderDetail(ReaderBrief):
    booklists: list[BookListBase]
