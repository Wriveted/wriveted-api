from typing import Any, List

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound, MultipleResultsFound
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.crud import CRUDBase
from app.models import Author
from app.schemas.author import AuthorCreateIn


class CRUDAuthor(CRUDBase[Author, AuthorCreateIn, Any]):

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

    def create_in_bulk(self, db: Session, *, bulk_author_data_in: List[AuthorCreateIn]):
        """
        Upsert via https://docs.sqlalchemy.org/en/14/dialects/postgresql.html#insert-on-conflict-upsert
        """
        insert_stmt = pg_insert(Author).on_conflict_do_nothing(
            #index_elements=['full_name']
        )

        values = [
            {
                "full_name": author.full_name,
                "last_name": author.last_name,
                "info": {} if author.info is None else author.info
            }
            for author in bulk_author_data_in
        ]
        db.execute(insert_stmt, values)

        db.flush()


author = CRUDAuthor(Author)