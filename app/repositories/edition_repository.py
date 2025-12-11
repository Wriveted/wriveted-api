"""
Edition repository - domain-focused data access for Edition domain.

Replaces the generic CRUDEdition class with proper repository pattern.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, List, Optional

from fastapi import HTTPException
from sqlalchemy import Select, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session
from structlog import get_logger

from app.models import Edition, Illustrator, Work
from app.models.work import WorkType
from app.repositories.author_repository import author_repository, first_last_to_name_key
from app.repositories.illustrator_repository import illustrator_repository
from app.repositories.labelset_repository import labelset_repository
from app.repositories.work_repository import work_repository
from app.schemas import is_url
from app.schemas.edition import EditionCreateIn, EditionUpdateIn
from app.schemas.work import WorkCreateIn
from app.services.cover_images import handle_new_edition_cover_image

logger = get_logger()


class EditionRepository(ABC):
    """Repository interface for Edition domain operations."""

    @abstractmethod
    def get(self, db: Session, isbn: str) -> Optional[Edition]:
        """Get an edition by ISBN."""
        pass

    @abstractmethod
    def get_or_404(self, db: Session, isbn: str) -> Edition:
        """Get an edition by ISBN or raise 404."""
        pass

    @abstractmethod
    def get_multi(self, db: Session, isbns: List[str]) -> List[Edition]:
        """Get multiple editions by ISBNs."""
        pass

    @abstractmethod
    def get_query(self, db: Session, isbn: Any) -> Select:
        """Build a query to get an edition by ISBN."""
        pass

    @abstractmethod
    def get_multi_query(
        self, db: Session, isbns: List[Any], *, order_by=None
    ) -> Select:
        """Build a query to get multiple editions by ISBNs."""
        pass

    @abstractmethod
    def get_all_query(self, db: Session, *, order_by=None) -> Select:
        """Build a query to get all editions."""
        pass

    @abstractmethod
    def create(
        self,
        db: Session,
        edition_data: EditionCreateIn,
        work: Work,
        illustrators: List[Illustrator],
        commit: bool = True,
    ) -> Edition:
        """Create a new edition."""
        pass

    @abstractmethod
    def create_in_bulk(
        self, session: Session, bulk_edition_data: List[EditionCreateIn]
    ) -> List[Edition]:
        """Create multiple editions in bulk with deduplication."""
        pass

    @abstractmethod
    def create_new_edition(
        self, session: Session, edition_data: EditionCreateIn, commit: bool = True
    ) -> Edition:
        """Create a new edition with get-or-create logic for related entities."""
        pass

    @abstractmethod
    def get_or_create_unhydrated(
        self, db: Session, isbn: str, commit: bool = True
    ) -> Edition:
        """Get or create an unhydrated edition placeholder."""
        pass

    @abstractmethod
    async def create_in_bulk_unhydrated(
        self, session: Session, isbn_list: List[str]
    ) -> tuple[List[str], int]:
        """Create multiple unhydrated editions in bulk."""
        pass

    @abstractmethod
    def update(
        self,
        db: Session,
        db_obj: Edition,
        obj_in: EditionUpdateIn,
        merge_dicts: bool = False,
        commit: bool = True,
    ) -> Edition:
        """Update an existing edition."""
        pass

    @abstractmethod
    def apply_pagination(self, query, skip: int = 0, limit: int = 100):
        """Apply pagination to a query."""
        pass


class EditionRepositoryImpl(EditionRepository):
    """Implementation of EditionRepository."""

    def get(self, db: Session, isbn: str) -> Optional[Edition]:
        """Get an edition by ISBN."""
        query = self.get_query(db, isbn)
        try:
            return db.execute(query).scalar_one()
        except NoResultFound:
            return None

    def get_or_404(self, db: Session, isbn: str) -> Edition:
        """Get an edition by ISBN or raise 404."""
        edition = self.get(db, isbn)
        if not edition:
            raise HTTPException(
                status_code=404, detail=f"Edition with ISBN {isbn} not found."
            )
        return edition

    def get_multi(self, db: Session, isbns: List[str]) -> List[Edition]:
        """Get multiple editions by ISBNs."""
        query = self.get_multi_query(db, isbns)
        return list(db.execute(query).scalars().all())

    def get_query(self, db: Session, isbn: Any) -> Select:
        """Build a query to get an edition by ISBN."""
        import app.services.editions as editions_service

        try:
            cleaned_isbn = editions_service.get_definitive_isbn(isbn)
        except (AssertionError, ValueError, TypeError):
            cleaned_isbn = ""

        return select(Edition).where(Edition.isbn == cleaned_isbn)

    def get_multi_query(
        self, db: Session, isbns: List[Any], *, order_by=None
    ) -> Select:
        """Build a query to get multiple editions by ISBNs."""
        import app.services.editions as editions_service

        return self.get_all_query(db, order_by=order_by).where(
            Edition.isbn.in_(editions_service.clean_isbns(isbns))
        )

    def get_all_query(self, db: Session, *, order_by=None) -> Select:
        """Build a query to get all editions."""
        query = select(Edition)
        if order_by is not None:
            query = query.order_by(order_by)
        return query

    def create(
        self,
        db: Session,
        edition_data: EditionCreateIn,
        work: Work,
        illustrators: List[Illustrator],
        commit: bool = True,
    ) -> Edition:
        """Create a new edition."""
        import app.services.editions as editions_service

        try:
            clean_isbn = editions_service.get_definitive_isbn(edition_data.isbn)
        except AssertionError:
            raise ValueError("Invalid ISBN")

        cover_url_data = edition_data.cover_url
        if cover_url_data and not is_url(cover_url_data):
            cover_url = handle_new_edition_cover_image(
                edition_isbn=clean_isbn,
                image_url_data=cover_url_data,
            )
            edition_data.cover_url = cover_url

        edition = Edition(
            leading_article=edition_data.leading_article,
            edition_title=edition_data.title,
            edition_subtitle=edition_data.subtitle,
            isbn=clean_isbn,
            cover_url=edition_data.cover_url,
            date_published=edition_data.date_published,
            info=edition_data.info.dict() if edition_data.info else {},
            work=work,
            illustrators=illustrators,
            hydrated_at=datetime.utcnow() if edition_data.hydrated else None,
        )
        db.add(edition)
        if commit:
            db.commit()
            db.refresh(edition)
        return edition

    def create_in_bulk(
        self, session: Session, bulk_edition_data: List[EditionCreateIn]
    ) -> List[Edition]:
        """Create multiple editions in bulk with deduplication."""
        import app.services.editions as editions_service

        seen_isbns = set()
        new_edition_data = []
        for edition_data in bulk_edition_data:
            try:
                definitive_isbn = editions_service.get_definitive_isbn(
                    edition_data.isbn
                )
            except (AssertionError, ValueError, TypeError):
                logger.warning(f"Invalid ISBN: {edition_data.isbn} - Skipping...")
                continue

            if definitive_isbn not in seen_isbns:
                seen_isbns.add(definitive_isbn)
                new_edition_data.append(edition_data)

        bulk_author_data = {}
        bulk_illustrator_data = {}
        bulk_series_titles = set()
        for edition_data in bulk_edition_data:
            if edition_data.authors is not None:
                for author_data in edition_data.authors:
                    bulk_author_data.setdefault(
                        first_last_to_name_key(
                            author_data.first_name, author_data.last_name
                        ),
                        author_data,
                    )
            if edition_data.illustrators is not None:
                for illustrator_data in edition_data.illustrators:
                    bulk_illustrator_data.setdefault(
                        first_last_to_name_key(
                            illustrator_data.first_name, illustrator_data.last_name
                        ),
                        illustrator_data,
                    )
            if (
                edition_data.series_name is not None
                and len(edition_data.series_name) > 0
            ):
                bulk_series_titles.add(edition_data.series_name)

        if len(bulk_author_data) > 0:
            author_repository.create_in_bulk(
                db=session, bulk_author_data_in=bulk_author_data.values()
            )
            logger.info("Authors created")

        if len(bulk_illustrator_data) > 0:
            illustrator_repository.create_in_bulk(
                db=session, bulk_illustrator_data_in=bulk_illustrator_data.values()
            )
            logger.info("Illustrators created")

        if len(bulk_series_titles) > 0:
            work_repository.bulk_create_series(
                session,
                bulk_series_data=bulk_series_titles,
            )
            logger.info("Series created")

        editions = []
        for edition_data in new_edition_data:
            editions.append(
                self.create_new_edition(session, edition_data=edition_data, commit=True)
            )
        logger.info("Work and Editions created")
        return editions

    def create_new_edition(
        self, session: Session, edition_data: EditionCreateIn, commit: bool = True
    ) -> Edition:
        """Create a new edition with get-or-create logic for related entities."""
        import app.services.editions as editions_service

        try:
            clean_isbn = editions_service.get_definitive_isbn(edition_data.isbn)
        except AssertionError:
            raise ValueError("Invalid ISBN")

        other_isbns = editions_service.clean_isbns(
            edition_data.other_isbns if edition_data.other_isbns is not None else []
        )
        other_isbns.discard(clean_isbn)

        edition: Edition = self.get(session, clean_isbn)
        hydrate = False
        if edition:
            if edition.hydrated:
                logger.info("Edition already exists. Skipping...")
                return
            else:
                hydrate = True

        work: Work = None
        for isbn in list(other_isbns) + [clean_isbn]:
            master_work = work_repository.find_by_isbn(session, isbn)
            if master_work:
                work = master_work
                break

        if edition_data.authors is None:
            edition_data.authors = []
        if edition_data.illustrators is None:
            edition_data.illustrators = []

        authors = [
            author_repository.get_or_create(session, author_data, commit=False)
            for author_data in edition_data.authors
        ]
        authors = list({author.id: author for author in authors}.values())
        illustrators = [
            illustrator_repository.get_or_create(
                session, illustrator_data, commit=False
            )
            for illustrator_data in edition_data.illustrators
        ]
        illustrators = list(
            {illustrator.id: illustrator for illustrator in illustrators}.values()
        )

        if edition_data.title and not work:
            work_create_data = WorkCreateIn(
                type=WorkType.BOOK,
                leading_article=edition_data.leading_article,
                title=edition_data.title,
                authors=edition_data.authors,
                series_name=edition_data.series_name,
                series_number=edition_data.series_number,
            )

            work = work_repository.get_or_create(
                session, work_data=work_create_data, authors=authors, commit=False
            )

            if edition_data.labelset and not edition_data.labelset.empty():
                labelset = labelset_repository.get_or_create(session, work)
                labelset = labelset_repository.patch(
                    session, labelset, edition_data.labelset, commit=False
                )

            if other_isbns:
                logger.info(
                    f"Associating {len(other_isbns)} other found editions under the same work for isbn {clean_isbn}"
                )
            for isbn in other_isbns:
                other_edition = self.get_or_create_unhydrated(session, isbn)
                work.editions.append(other_edition)

        if hydrate:
            update_data = EditionUpdateIn(**edition_data.dict())
            update_data.work_id = work.id if work else None
            update_data.illustrators = illustrators
            update_data.hydrated_at = datetime.utcnow()
            edition = self.update(
                db=session,
                db_obj=edition,
                obj_in=update_data,
                commit=commit,
            )
        else:
            edition = self.create(
                db=session,
                edition_data=edition_data,
                work=work,
                illustrators=illustrators,
                commit=commit,
            )

        return edition

    def get_or_create_unhydrated(
        self, db: Session, isbn: str, commit: bool = True
    ) -> Edition:
        """Get or create an unhydrated edition placeholder."""
        import app.services.editions as editions_service

        edition = self.get(db, isbn)
        if not edition:
            edition = Edition(isbn=editions_service.get_definitive_isbn(isbn))
            db.add(edition)
            if commit:
                db.commit()

        return edition

    async def create_in_bulk_unhydrated(
        self, session: Session, isbn_list: List[str]
    ) -> tuple[List[str], int]:
        """Create multiple unhydrated editions in bulk."""
        import app.services.editions as editions_service

        clean_isbn_list = editions_service.clean_isbns(isbn_list)
        editions = [{"isbn": isbn} for isbn in clean_isbn_list]

        previous_count = session.execute(select(func.count(Edition.id))).scalar_one()

        if editions:
            stmt = insert(Edition).on_conflict_do_nothing()
            session.execute(stmt, editions)
            session.commit()

        new_count = session.execute(select(func.count(Edition.id))).scalar_one()
        num_created = new_count - previous_count

        logger.info(f"{num_created} unhydrated editions created")
        return clean_isbn_list, num_created

    def update(
        self,
        db: Session,
        db_obj: Edition,
        obj_in: EditionUpdateIn,
        merge_dicts: bool = False,
        commit: bool = True,
    ) -> Edition:
        """Update an existing edition."""
        from sqlalchemy.ext.mutable import MutableDict

        from app.utils.dict_utils import deep_merge_dicts

        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)

        for field, value in update_data.items():
            if hasattr(db_obj, field):
                attr = getattr(db_obj, field)
                if merge_dicts and isinstance(attr, dict):
                    deep_merge_dicts(attr, value)
                else:
                    setattr(db_obj, field, value)
                if isinstance(attr, MutableDict):
                    attr.changed()
        db.add(db_obj)
        if commit:
            db.commit()
            db.refresh(db_obj)
        return db_obj

    def apply_pagination(self, query, skip: int = 0, limit: int = 100):
        """Apply pagination to a query."""
        return query.offset(skip).limit(limit)


# Singleton instance
edition_repository = EditionRepositoryImpl()
