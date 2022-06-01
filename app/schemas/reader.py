from datetime import datetime
from pydantic import BaseModel
from app.schemas.booklist import BookListBase

from app.schemas.recommendations import ReadingAbilityKey
from app.schemas.user import ParentIdentity, UserDetail, UserIdentity


class ReadingPreferences(BaseModel):
    age: int | None
    reading_ability: ReadingAbilityKey | None
    last_visited: datetime | None


class ReaderIdentity(UserIdentity):
    username: str
    first_name: str
    last_name_initial: str


class ReaderBrief(ReaderIdentity):
    reading_preferences: ReadingPreferences
    parent: ParentIdentity | None


class ReaderDetail(UserDetail, ReaderBrief):
    booklists: list[BookListBase]
    pass
