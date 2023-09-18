from __future__ import annotations

from pydantic import BaseModel, field_validator, validator
from sqlalchemy.orm.dynamic import AppenderQuery

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
    first_name: str | None = None
    last_name_initial: str | None = None


class ReaderIdentity(ReaderBase, UserIdentity):
    pass


class ReaderBrief(ReaderBase, UserBrief):
    huey_attributes: HueyAttributes
    parent: UserIdentity | None = None


class ReaderDetail(ReaderBrief, UserDetail):
    booklists: list[BookListBase]
    reading_path: ReadingPath = None
    special_lists: SpecialLists = None
    collection: CollectionBrief | None = None

    # TODO[pydantic]: We couldn't refactor the `validator`, please replace it by `field_validator` manually.
    # Check https://docs.pydantic.dev/dev-v2/migration/#changes-to-validators for more information.
    @validator("reading_path", pre=True, always=True)
    def grab_pathway_lists(cls, v, values):
        lists = values.get("booklists", None)
        output = {}
        # get the first booklist matching each required name (with null safeties)
        output["read_now"] = next(
            iter([list for list in lists if list.name == "Books To Read Now"] or []),
            None,
        )
        output["read_next"] = next(
            iter([list for list in lists if list.name == "Books To Read Next"] or []),
            None,
        )
        return output

    # TODO[pydantic]: We couldn't refactor the `validator`, please replace it by `field_validator` manually.
    # Check https://docs.pydantic.dev/dev-v2/migration/#changes-to-validators for more information.
    @validator("special_lists", pre=True, always=True)
    def grab_special_lists(cls, v, values):
        lists = values.get("booklists", None)
        output = {}
        # get the first booklist matching each required name (with null safeties)
        output["read_books"] = next(
            iter([list for list in lists if list.name == "Books I've Read"] or []), None
        )
        output["favourite_books"] = next(
            iter([list for list in lists if list.name == "My Favourite Books"] or []),
            None,
        )
        output["suggested_books"] = next(
            iter([list for list in lists if list.name == "Suggested Books"] or []),
            None,
        )
        return output

    @field_validator("booklists", mode="before")
    @classmethod
    def limit_booklists(cls, v):
        return v[:5] if isinstance(v, (AppenderQuery, list)) else v
