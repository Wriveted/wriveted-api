from multiprocessing import get_logger
from sqlite3 import IntegrityError
from typing import Any, List, Optional
from sqlalchemy import and_, insert, select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.crud import CRUDBase
from app.models import Work, Author, Series
from app.models.edition import Edition
from app.models.work import WorkType
from app.models.series_works_association import series_works_association_table
from app.schemas.work import WorkCreateIn

logger = get_logger()


class CRUDWork(CRUDBase[Work, WorkCreateIn, Any]):

    # def create_in_bulk(self, db: Session, work_data: List[WorkCreateIn]) -> List[Work]:
    #     pass

    def get_or_create(
        self, db: Session, work_data: WorkCreateIn, authors: List[Author], commit=True
    ) -> Work:

        author_ids = [a.id for a in authors]

        q = (
            select(Work)
            .where(Work.type == work_data.type)
            .where(Work.title == work_data.title)
            .where(Work.authors.any(Author.id.in_(author_ids)))
        )

        try:
            work = db.execute(q).scalar_one()
        except NoResultFound:
            work = Work(
                type=WorkType.BOOK,
                title=work_data.title,
                info=work_data.info,
                authors=authors,
            )
            db.add(work)
            db.flush()

            if work_data.series_name is not None:
                series = self.get_or_create_series(db, work_data.series_name)
                # add the work to the series, appending the series_number/order_id if applicable
                try:
                    # using SQLAlchemy Core as the association table doesn't have an ORM object.
                    # probably a TODO.
                    series_works_values = {"series_id": series.id, "work_id": work.id}
                    if work_data.series_number:
                        series_works_values["order_id"] = work_data.series_number
                    db.execute(
                        insert(series_works_association_table).values(
                            **series_works_values
                        )
                    )
                except IntegrityError as e:
                    logger.warning(
                        "Database integrity error while adding series", exc_info=e
                    )

            if commit:
                db.commit()
                db.refresh(work)

        return work

    def get_or_create_series(self, db, series_title):
        try:
            series = db.execute(
                select(Series).where(Series.title == series_title)
            ).scalar_one()
        except NoResultFound:
            series = Series(title=series_title)
        return series

    def bulk_create_series(self, db: Session, bulk_series_data: list[str]):
        insert_stmt = pg_insert(Series).on_conflict_do_nothing()
        values = [{"title": title} for title in bulk_series_data]

        db.execute(insert_stmt, values)
        db.flush()

    def find_by_isbn(self, db: Session, isbn: str) -> Optional[Work]:
        q = select(Work).where(Work.editions.any(Edition.isbn == isbn))
        return db.execute(q).scalar_one_or_none()

    def find_by_title_and_author_key(self, db: Session, title: str, author_key: str):
        q = select(Work).where(
            and_(
                Work.authors.any(Author.name_key == author_key),
                Work.title == title,
            )
        )
        return db.execute(q).scalar_one_or_none()


work = CRUDWork(Work)
