from typing import Any, List, Optional

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

from app.crud import CRUDBase
from app.models import Author
from app.schemas.author import AuthorCreateIn


def first_last_to_name_key(first_name: str, last_name: str):
    return "".join(
        char for char in f"{first_name or ''}{last_name}".lower() if char.isalnum()
    )


class CRUDAuthor(CRUDBase[Author, AuthorCreateIn, Any]):
    def get_or_create(
        self, db: Session, author_data: AuthorCreateIn, commit=True
    ) -> Author:

        q = select(Author).where(
            Author.name_key
            == first_last_to_name_key(author_data.first_name, author_data.last_name)
        )
        try:
            author = db.execute(q).scalar_one()
        except NoResultFound:
            author = self.create(db, obj_in=author_data, commit=commit)

        return author

    def create_in_bulk(self, db: Session, *, bulk_author_data_in: List[AuthorCreateIn]):
        """
        Upsert via https://docs.sqlalchemy.org/en/14/dialects/postgresql.html#insert-on-conflict-upsert

        Note this relies on the clearly incorrect assumption that Author's names are unique.
        """
        insert_stmt = pg_insert(Author).on_conflict_do_nothing(
            # index_elements=['full_name']
        )

        values = [
            {
                "first_name": author.first_name,
                "last_name": author.last_name,
                "info": {} if author.info is None else author.info,
            }
            for author in bulk_author_data_in
        ]
        db.execute(insert_stmt, values)

        db.flush()

    def get_all_with_optional_filters_query(
        self,
        db: Session,
        query_string: Optional[str] = None,
    ):
        author_query = self.get_all_query(db=db)

        if query_string is not None:
            # https://docs.sqlalchemy.org/en/14/dialects/postgresql.html?highlight=search#full-text-search
            author_query = author_query.where(
                func.lower(Author.name_key).contains(query_string.lower())
            )

        return author_query

    def get_all_with_optional_filters(
        self,
        db: Session,
        query_string: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ):
        optional_filters = {
            "query_string": query_string,
        }
        query = self.apply_pagination(
            self.get_all_with_optional_filters_query(db=db, **optional_filters),
            skip=skip,
            limit=limit,
        )
        return db.scalars(query).all()


author = CRUDAuthor(Author)
