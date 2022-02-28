from typing import Any, List

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, Query
from structlog import get_logger

from app import crud
from app.crud import CRUDBase
from app.crud.author import author as crud_author, first_last_to_name_key
from app.crud.work import work as crud_work
from app.crud.illustrator import illustrator as crud_illustrator

from app.models import Edition, Work, Illustrator
from app.models.work import WorkType
from app.schemas.edition import EditionCreateIn
from app.schemas.work import WorkCreateIn, SeriesCreateIn

import app.services.editions as editions_service


logger = get_logger()


class CRUDEdition(CRUDBase[Edition, Any, Any]):
    """
    We use ISBN in the CRUD layer instead of the database ID
    """

    def get_query(self, db: Session, id: Any) -> Query:
        try:
            cleaned_isbn = editions_service.get_definitive_isbn(id)
        except:
            cleaned_isbn = ""

        return select(Edition).where(Edition.isbn == cleaned_isbn)

    def get_multi_query(self, db: Session, ids: List[Any], *, order_by=None) -> Query:
        return self.get_all_query(db, order_by=order_by).where(
            Edition.isbn.in_(editions_service.clean_isbns(ids))
        )

    def create(
        self,
        db: Session,
        edition_data: EditionCreateIn,
        work: Work,
        illustrators: List[Illustrator],
        commit=True,
    ) -> Edition:
        """
        Insert an edition row in the table assuming the related objects exist.

        See `create_new_edition` to also get_or_create the related Author/Work/Illustrator
        objects.
        """
        edition = Edition(
            edition_title=edition_data.title,
            isbn=editions_service.get_definitive_isbn(edition_data.isbn),
            cover_url=edition_data.cover_url,
            info=edition_data.info.dict(),
            work=work,
            illustrators=illustrators,
        )
        db.add(edition)
        if commit:
            db.commit()
            db.refresh(edition)
        return edition

    def create_in_bulk(self, session, bulk_edition_data: List[EditionCreateIn]):
        # Need to account for new authors, works, and series created
        # in a single upload and referenced multiple times. Unfortunately we
        # can't just commit these ORM objects all at the end as we would likely
        # violate the database constraints - e.g. adding the series "Harry Potter"
        # multiple times.
        # A more performant approach might be to first process all the authors and
        # works, then the illustrators then the editions.
        #
        # Working end to end is more important than working fast right now though, so
        # this is left as a future improvement.

        # There might be duplicate editions in the input, so we keep a list of what
        # we've seen
        seen_isbns = set()
        new_edition_data = []
        for edition_data in bulk_edition_data:
            try:
                definitive_isbn = editions_service.get_definitive_isbn(edition_data.isbn)
            except:
                logger.info("Invalid ISBN. Skipping...")
                continue

            if definitive_isbn not in seen_isbns:
                seen_isbns.add(definitive_isbn)
                new_edition_data.append(edition_data)

        # Dedupe Author data by a name key: lowercase, alphanumerics only, first_name + last_name
        bulk_author_data = {}
        bulk_series_titles = set()
        for edition_data in bulk_edition_data:
            for author_data in edition_data.authors:
                bulk_author_data.setdefault(
                    first_last_to_name_key(author_data.first_name, author_data.last_name),
                    author_data)
            if (
                edition_data.series_title is not None
                and len(edition_data.series_title) > 0
            ):
                bulk_series_titles.add(edition_data.series_title)

        if len(bulk_author_data) > 0:
            crud.author.create_in_bulk(
                db=session, bulk_author_data_in=bulk_author_data.values()
            )
            logger.info("Authors created")

        # Series
        if len(bulk_series_titles) > 0:
            crud.work.bulk_create_series(
                session,
                bulk_series_data=[
                    SeriesCreateIn(title=series_title)
                    for series_title in bulk_series_titles
                ],
            )
        logger.info("Series created")

        # TODO keep bulkifying this...
        # Work next

        editions = []
        for edition_data in new_edition_data:
            editions.append(
                self.create_new_edition(session, edition_data=edition_data, commit=True)
            )
        logger.info("Work, Illustrators and Editions created")
        return editions

    def create_new_edition(self, session, edition_data: EditionCreateIn, commit=True):
        # Get or create the authors
        authors = [
            crud_author.get_or_create(session, author_data, commit=False)
            for author_data in edition_data.authors
        ]

        # Get or create the work
        work_create_data = WorkCreateIn(
            type=WorkType.BOOK,
            title=edition_data.work_title
            if edition_data.work_title is not None
            else edition_data.title,
            authors=edition_data.authors,
            info=edition_data.work_info,
            series_title=edition_data.work_info.series_title,
        )

        work = crud_work.get_or_create(
            session, work_data=work_create_data, authors=authors, commit=False
        )
        # Get or create the illustrators
        illustrators = [
            crud_illustrator.get_or_create(session, illustrator_data, commit=False)
            for illustrator_data in edition_data.illustrators
        ]
        # Then, at last create the edition - raising an error if it already existed
        edition = self.create(
            db=session,
            edition_data=edition_data,
            work=work,
            illustrators=illustrators,
            commit=commit,
        )
        return edition


    # To speed up the inserts, we've opted out orm features to track each object and retrieve each pk after insertion.
    # but since we know already have the isbns, i.e the pk's that are being inserted, we can refer to them later anyway.
    # After ensuring the list is added to the db, this returns the list of cleaned pk's.
    async def create_in_bulk_unhydrated(self, session: Session, isbn_list: List[str]):
        clean_isbn_list = editions_service.clean_isbns(isbn_list)
        editions = [{"isbn" : isbn} for isbn in clean_isbn_list]

        previous_count = session.execute(select(func.count(Edition.id))).scalar_one()

        stmt = insert(Edition).on_conflict_do_nothing()
        session.execute(stmt, editions)
        session.commit()

        new_count = session.execute(select(func.count(Edition.id))).scalar_one()
        # can't seem to track how many conflicts the commit generates, so our best way
        # of tracking the amount that were actually created is to just generate a count diff
        num_created = new_count - previous_count

        logger.info(f"{num_created} unhydrated editions created")
        return clean_isbn_list, num_created


edition = CRUDEdition(Edition)
