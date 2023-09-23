from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, field_validator, model_validator
from sqlalchemy.orm.dynamic import AppenderQuery

from app.models.user import UserAccountType
from app.schemas.booklist import BookListBase
from app.schemas.collection import CollectionBrief
from app.schemas.users.huey_attributes import HueyAttributes
from app.schemas.users.user import UserDetail
from app.schemas.users.user_identity import UserBrief, UserIdentity


class ReadingPath(BaseModel):
    read_now: BookListBase | None = None
    read_next: BookListBase | None = None


class SpecialLists(BaseModel):
    read_books: BookListBase | None = None
    favorite_books: BookListBase | None = None
    suggested_books: BookListBase | None = None


class ReaderBase(BaseModel):
    # type: Literal[UserAccountType.STUDENT, UserAccountType.PUBLIC]
    first_name: str | None = None
    last_name_initial: str | None = None


class ReaderIdentity(ReaderBase, UserIdentity):
    pass


class ReaderBrief(ReaderBase, UserBrief):
    huey_attributes: HueyAttributes
    parent: UserIdentity | None = None


class ReaderDetail(ReaderBrief, UserDetail):
    booklists: list[BookListBase] = []
    reading_path: ReadingPath = None
    special_lists: SpecialLists = None
    collection: CollectionBrief | None = None

    @model_validator(mode="after")
    def validate_reading_pathway_lists(self):
        # get the first booklist matching each required name (with null safeties)
        read_now_booklist = next(
            iter(
                [list for list in self.booklists if list.name == "Books To Read Now"]
                or []
            ),
            None,
        )
        read_next_booklist = next(
            iter(
                [list for list in self.booklists if list.name == "Books To Read Next"]
                or []
            ),
            None,
        )
        self.reading_path = ReadingPath(
            read_now=read_now_booklist, read_next=read_next_booklist
        )
        return self

    @model_validator(mode="after")
    def grab_special_lists(self):
        lists = self.booklists

        # get the first booklist matching each required name (with null safeties)
        read_booklist = next(
            iter([list for list in lists if list.name == "Books I've Read"] or []), None
        )
        favourite_booklist = next(
            iter([list for list in lists if list.name == "My Favourite Books"] or []),
            None,
        )
        suggested_booklist = next(
            iter([list for list in lists if list.name == "Suggested Books"] or []),
            None,
        )
        self.special_lists = SpecialLists(
            read_books=read_booklist,
            favorite_books=favourite_booklist,
            suggested_books=suggested_booklist,
        )
        return self

    @field_validator("booklists", mode="before")
    @classmethod
    def limit_booklists(cls, v) -> list[BookListBase]:
        return v[:5] if isinstance(v, (AppenderQuery, list)) else v


class PublicReaderDetail(ReaderDetail):
    type: Literal[UserAccountType.PUBLIC]
