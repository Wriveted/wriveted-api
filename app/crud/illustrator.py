from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

from app.crud import CRUDBase
from app.models import Illustrator
from app.schemas.illustrator import IllustratorCreateIn


def first_last_to_name_key(first_name: str, last_name: str):
    return "".join(
        char for char in f"{first_name or ''}{last_name}".lower() if char.isalnum()
    )


class CRUDIllustrator(CRUDBase[Illustrator, Any, Any]):
    def get_or_create(
        self, db: Session, data: IllustratorCreateIn, commit=True
    ) -> Illustrator:
        q = select(Illustrator).where(
            Illustrator.name_key
            == first_last_to_name_key(data.first_name, data.last_name)
        )
        try:
            orm_obj = db.execute(q).scalar_one()
        except NoResultFound:
            orm_obj = self.create(db, obj_in=data, commit=commit)
        return orm_obj

    def create_in_bulk(
        self, db: Session, *, bulk_illustrator_data_in: list[IllustratorCreateIn]
    ):
        """
        Upsert via https://docs.sqlalchemy.org/en/14/dialects/postgresql.html#insert-on-conflict-upsert

        Note this relies on the clearly incorrect assumption that Illustrator's names are unique.
        """
        insert_stmt = pg_insert(Illustrator).on_conflict_do_nothing(
            # index_elements=['full_name']
        )

        values = [
            {
                "first_name": illustrator.first_name,
                "last_name": illustrator.last_name,
                "info": {} if illustrator.info is None else illustrator.info,
            }
            for illustrator in bulk_illustrator_data_in
        ]
        db.execute(insert_stmt, values)

        db.flush()


illustrator = CRUDIllustrator(Illustrator)
