from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound, MultipleResultsFound
from sqlalchemy.orm import Session

from app.crud import CRUDBase
from app.models import Author
from app.schemas.author import AuthorCreateIn


class CRUDAuthor(CRUDBase[Author, Any, Any]):

    def get_or_create(self, db: Session, author_data: AuthorCreateIn, commit=True) -> Author:

        q = select(Author).where(Author.full_name == author_data.full_name)
        try:
            author = db.execute(q).scalar_one()
        except NoResultFound:
            author = self.create(db, obj_in=author_data, commit=commit)
        except MultipleResultsFound:
            # We don't currently impose that an author's full name must be
            # unique at the database layer, so we need to deal with the
            # occasional duplicate
            print("Duplicate author found. Taking first", author_data.full_name)
            author = db.execute(q).scalars().first()
        return author


