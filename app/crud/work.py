from typing import Any, List

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session, Query

from app import crud
from app.crud import CRUDBase
from app.models import Work, Author, Series
from app.models.work import WorkType
from app.schemas.work import WorkCreateIn


class CRUDWork(CRUDBase[Work, WorkCreateIn, Any]):

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
            if work_data.series_title is not None:
                series = self.get_or_create_series(db, work_data.series_title)
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
