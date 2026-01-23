"""
Work repository - domain-focused data access for Works domain.

Replaces the generic CRUDWork class with proper repository pattern.
"""

import re
from abc import ABC, abstractmethod
from typing import Any, List, Optional

from fastapi import HTTPException
from sqlalchemy import and_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from structlog import get_logger

from app.models import Author, Series, Work
from app.models.author_work_association import author_work_association_table
from app.models.edition import Edition
from app.models.series_works_association import series_works_association_table
from app.models.work import WorkType
from app.schemas.work import WorkCreateIn

logger = get_logger()


class WorkRepository(ABC):
    """Repository interface for Work domain operations."""

    @abstractmethod
    def get_by_id(self, db: Session, work_id: int) -> Optional[Work]:
        """Get a work by its ID."""
        pass

    @abstractmethod
    async def acreate(
        self, db: AsyncSession, obj_in: WorkCreateIn, commit: bool = True
    ) -> Work:
        """Create work with nested authors - async version."""
        pass

    @abstractmethod
    def get_or_create(
        self,
        db: Session,
        work_data: WorkCreateIn,
        authors: List[Author],
        commit: bool = True,
    ) -> Work:
        """Get or create a work by title and authors."""
        pass

    @abstractmethod
    def series_title_to_key(self, series_title: str) -> str:
        """Convert series title to key for lookup."""
        pass

    @abstractmethod
    def get_or_create_series(self, db: Session, series_title: str) -> Series:
        """Get or create a series by title."""
        pass

    @abstractmethod
    async def aget_or_create_series(
        self, db: AsyncSession, series_title: str
    ) -> Series:
        """Async version of get_or_create_series."""
        pass

    @abstractmethod
    def bulk_create_series(self, db: Session, bulk_series_data: list[str]) -> None:
        """Bulk create series."""
        pass

    @abstractmethod
    def find_by_isbn(self, db: Session, isbn: str) -> Optional[Work]:
        """Find a work by ISBN (via editions)."""
        pass

    @abstractmethod
    def find_by_title_and_author_key(
        self, db: Session, title: str, author_key: str
    ) -> Optional[Work]:
        """Find a work by title and author key."""
        pass

    @abstractmethod
    def create(self, db: Session, obj_in: WorkCreateIn, commit: bool = True) -> Work:
        """Create a work."""
        pass

    @abstractmethod
    def update(
        self, db: Session, db_obj: Work, obj_in: Any, commit: bool = True
    ) -> Work:
        """Update a work."""
        pass

    @abstractmethod
    def get_or_404(self, db: Session, id: int) -> Work:
        """Get a work by ID or raise 404."""
        pass

    @abstractmethod
    def get_all_query(self, db: Session):
        """Get a query for all works."""
        pass

    @abstractmethod
    def apply_pagination(self, query, skip: int = 0, limit: int = 100):
        """Apply pagination to a query."""
        pass

    @abstractmethod
    def remove(self, db: Session, id: int, commit: bool = True) -> Work:
        """Delete a work by ID."""
        pass


class WorkRepositoryImpl(WorkRepository):
    """Implementation of WorkRepository."""

    def get_by_id(self, db: Session, work_id: int) -> Optional[Work]:
        """Get a work by its ID."""
        return db.get(Work, work_id)

    async def acreate(
        self, db: AsyncSession, obj_in: WorkCreateIn, commit: bool = True
    ) -> Work:
        """Create work with nested authors - async version."""
        # First, create or get the authors
        authors = []
        for author_data in obj_in.authors:
            full_name = (author_data.first_name or "") + author_data.last_name
            name_key = re.sub(r"\W|_", "", full_name).lower()

            existing_author = await db.execute(
                select(Author).where(Author.name_key == name_key)
            )
            existing = existing_author.scalar_one_or_none()

            if existing:
                authors.append(existing)
            else:
                new_author = Author(
                    first_name=author_data.first_name,
                    last_name=author_data.last_name,
                    info=author_data.info or {},
                )
                db.add(new_author)
                await db.flush()
                authors.append(new_author)

        work_data = {
            "type": obj_in.type,
            "title": obj_in.title,
            "leading_article": obj_in.leading_article,
            "subtitle": obj_in.subtitle,
            "info": obj_in.info or {},
        }

        work = Work(**work_data)
        db.add(work)
        await db.flush()

        author_ids = [a.id for a in authors]
        if author_ids:
            await db.execute(
                pg_insert(author_work_association_table)
                .on_conflict_do_nothing()
                .values([{"work_id": work.id, "author_id": aid} for aid in author_ids])
            )

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
        self,
        db: Session,
        work_data: WorkCreateIn,
        authors: List[Author],
        commit: bool = True,
    ) -> Work:
        """Get or create a work by title and authors."""
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

            db.execute(
                pg_insert(author_work_association_table)
                .on_conflict_do_nothing()
                .values([{"work_id": work.id, "author_id": aid} for aid in author_ids])
            )

            if work_data.series_name is not None:
                series = self.get_or_create_series(db, work_data.series_name)
                series_works_values = {"series_id": series.id, "work_id": work.id}
                if work_data.series_number:
                    series_works_values["order_id"] = work_data.series_number
                try:
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

    def series_title_to_key(self, series_title: str) -> str:
        """Convert series title to key for lookup."""
        return re.sub("(^(\\w*the ))|(^(\\w*a ))|[^a-z0-9]", "", series_title.lower())

    def get_or_create_series(self, db: Session, series_title: str) -> Series:
        """Get or create a series by title."""
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

    def bulk_create_series(self, db: Session, bulk_series_data: list[str]) -> None:
        """Bulk create series."""
        insert_stmt = pg_insert(Series).on_conflict_do_nothing()
        values = [{"title": title} for title in bulk_series_data]

        db.execute(insert_stmt, values)
        db.flush()

    def find_by_isbn(self, db: Session, isbn: str) -> Optional[Work]:
        """Find a work by ISBN (via editions)."""
        q = select(Work).where(Work.editions.any(Edition.isbn == isbn))
        return db.execute(q).scalar_one_or_none()

    def find_by_title_and_author_key(
        self, db: Session, title: str, author_key: str
    ) -> Optional[Work]:
        """Find a work by title and author key."""
        q = select(Work).where(
            and_(
                Work.authors.any(Author.name_key == author_key),
                Work.title == title,
            )
        )
        return db.execute(q).scalar_one_or_none()

    def create(self, db: Session, obj_in: WorkCreateIn, commit: bool = True) -> Work:
        """Create a work."""
        orm_obj = Work(**obj_in.model_dump())
        db.add(orm_obj)
        if commit:
            db.commit()
            db.refresh(orm_obj)
        return orm_obj

    def update(
        self, db: Session, db_obj: Work, obj_in: Any, commit: bool = True
    ) -> Work:
        """Update a work."""
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        if commit:
            db.commit()
            db.refresh(db_obj)
        return db_obj

    def get_or_404(self, db: Session, id: int) -> Work:
        """Get a work by ID or raise 404."""
        work = self.get_by_id(db, id)
        if not work:
            raise HTTPException(status_code=404, detail=f"Work with id {id} not found")
        return work

    def get_all_query(self, db: Session):
        """Get a query for all works."""
        return select(Work)

    def apply_pagination(self, query, skip: int = 0, limit: int = 100):
        """Apply pagination to a query."""
        return query.offset(skip).limit(limit)

    def remove(self, db: Session, id: int, commit: bool = True) -> Work:
        """Delete a work by ID."""
        work = self.get_by_id(db, id)
        if work:
            db.delete(work)
            if commit:
                db.commit()
        return work


# Singleton instance
work_repository = WorkRepositoryImpl()
