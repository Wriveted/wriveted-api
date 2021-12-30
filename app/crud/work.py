from typing import Any, List

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session, Query
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app import crud
from app.crud import CRUDBase
from app.models import Work, Author, Series
from app.models.work import WorkType
from app.schemas.work import WorkCreateIn, SeriesCreateIn


class CRUDWork(CRUDBase[Work, WorkCreateIn, Any]):

    # def create_in_bulk(self, db: Session, work_data: List[WorkCreateIn]) -> List[Work]:
    #     pass

    def get_or_create(self,
                      db: Session,
                      work_data: WorkCreateIn,
                      authors: List[Author],
                      commit=True) -> Work:

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
                authors=authors
            )
            if work_data.series is not None:
                series = self.get_or_create_series(db, work_data.series.title)
                work.series.append(series)

            db.add(work)
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

    def bulk_create_series(self, db: Session, bulk_series_data: List[SeriesCreateIn]):
        print(bulk_series_data)
        insert_stmt = pg_insert(Series).on_conflict_do_nothing()
        values = [
            {
                "title": series.title,
                "info": {} if series.info is None else series.info
            }
            for series in bulk_series_data
        ]

        db.execute(insert_stmt, values)
        db.flush()


work = CRUDWork(Work)
