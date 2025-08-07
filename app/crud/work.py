import re
from multiprocessing import get_logger
from typing import Any, List, Optional

from sqlalchemy import and_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
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

    async def acreate(
        self, db: AsyncSession, *, obj_in: WorkCreateIn, commit=True
    ) -> Work:
        """Create work with nested authors - async version."""
        # First, create or get the authors
        authors = []
        for author_data in obj_in.authors:
            # Generate the name_key as computed by the database
            # name_key = LOWER(REGEXP_REPLACE(first_name || last_name, '\\W|_', '', 'g'))
            full_name = (author_data.first_name or "") + author_data.last_name
            import re

            name_key = re.sub(r"\W|_", "", full_name).lower()

            # Check if author already exists by name_key
            existing_author = await db.execute(
                select(Author).where(Author.name_key == name_key)
            )
            existing = existing_author.scalar_one_or_none()

            if existing:
                authors.append(existing)
            else:
                # Create new author - let database compute name_key
                new_author = Author(
                    first_name=author_data.first_name,
                    last_name=author_data.last_name,
                    info=author_data.info or {},
                )
                db.add(new_author)
                await db.flush()  # Get the ID
                authors.append(new_author)

        # Create the work
        work_data = {
            "type": obj_in.type,
            "title": obj_in.title,
            "leading_article": obj_in.leading_article,
            "subtitle": obj_in.subtitle,
            "info": obj_in.info or {},
        }

        work = Work(**work_data)
        db.add(work)
        await db.flush()  # Get the work ID

        # Create author-work associations
        author_ids = [a.id for a in authors]
        if author_ids:
            await db.execute(
                pg_insert(author_work_association_table)
                .on_conflict_do_nothing()
                .values([{"work_id": work.id, "author_id": aid} for aid in author_ids])
            )

        # Handle series if provided
        if obj_in.series_name:
            series = await self.aget_or_create_series(db, obj_in.series_name)
            series_works_values = {"series_id": series.id, "work_id": work.id}
            if obj_in.series_number:
                series_works_values["order_id"] = obj_in.series_number

            try:
                await db.execute(
                    pg_insert(series_works_association_table).values(
                        **series_works_values
                    )
                )
            except IntegrityError as e:
                logger.warning(
                    "Database integrity error while adding series", exc_info=e
                )

        if commit:
            await db.commit()
            await db.refresh(work)

        return work

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

    async def aget_or_create_series(
        self, db: AsyncSession, series_title: str
    ) -> Series:
        """Async version of get_or_create_series."""
        title_key = self.series_title_to_key(series_title)
        try:
            result = await db.execute(
                select(Series).where(Series.title_key == title_key)
            )
            series = result.scalar_one()
        except NoResultFound:
            series = Series(title=series_title)
            db.add(series)
            await db.flush()
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
