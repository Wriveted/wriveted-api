from __future__ import annotations

from app.schemas.booklist import BookListBase
from app.schemas.users import ParentIdentity
from app.schemas.users.reading_preferences import ReadingPreferences
from app.schemas.users.user_identity import ReaderIdentity


class ReaderBrief(ReaderIdentity):
    reading_preferences: ReadingPreferences
    parent: ParentIdentity | None


class ReaderDetail(ReaderBrief):
    booklists: list[BookListBase]
