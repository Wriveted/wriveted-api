import re
from multiprocessing import get_logger
from typing import Any, List, Optional

from sqlalchemy import and_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm import Session

from app.crud import CRUDBase
from app.models import Author, Series, Work
from app.models.author_work_association import author_work_association_table
from app.models.edition import Edition
from app.models.series_works_association import series_works_association_table
from app.models.work import WorkType
from app.schemas.work import WorkCreateIn

logger = get_logger()


class CRUDWork(CRUDBase[Work, WorkCreateIn, Any]):
    # def create_in_bulk(self, db: Session, work_data: List[WorkCreateIn]) -> List[Work]:
    #     pass

    def get_or_create(
        self, db: Session, work_data: WorkCreateIn, authors: List[Author], commit=True
    ) -> Work:
        author_ids = list(set(a.id for a in authors))

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
            )
            db.add(work)
            db.flush()

            # add the authors to the work
            db.execute(
                pg_insert(author_work_association_table)
                .on_conflict_do_nothing()
                .values([{"work_id": work.id, "author_id": aid} for aid in author_ids])
            )

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
                        pg_insert(series_works_association_table).values(
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

    def series_title_to_key(self, series_title: str):
        return re.sub("(^(\\w*the ))|(^(\\w*a ))|[^a-z0-9]", "", series_title.lower())

    def get_or_create_series(self, db, series_title):
        title_key = self.series_title_to_key(series_title)
        try:
            series = db.execute(
                select(Series).where(Series.title_key == title_key)
            ).scalar_one()
        except NoResultFound:
            series = Series(title=series_title)
            db.add(series)
            db.flush()
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
