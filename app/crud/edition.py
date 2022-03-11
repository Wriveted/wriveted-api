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
from app.schemas.work import WorkCreateIn

import app.services.editions as editions_service


logger = get_logger()


class CRUDEdition(CRUDBase[Edition, Any, Any]):
    """
    We use ISBN in the CRUD layer instead of the database ID
    """
    # These are overrides of CRDUBase. Do not rename. 
    # Can be executed by using self.get() and self.get_multi() respectively
    
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

    # -------------------------------------------------------

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
            leading_article=edition_data.leading_article,
            edition_title=edition_data.title,
            edition_subtitle=edition_data.subtitle,
            isbn=editions_service.get_definitive_isbn(edition_data.isbn),
            cover_url=edition_data.cover_url,
            date_published=edition_data.date_published,
            info=edition_data.info.dict(),
            work=work,
            illustrators=illustrators,
            hydrated=edition_data.hydrated
        )
        db.add(edition)
        if commit:
            db.commit()
            db.refresh(edition)
        return edition


    def update(
        self,
        db: Session,
        edition_data: EditionCreateIn,
        work: Work,
        illustrators: List[Illustrator],
        commit=True,
    ) -> Edition:
        """
        Update an edition row in the table assuming the related objects exist.
        """
        edition: Edition = self.get(db, editions_service.get_definitive_isbn(edition_data.isbn))

        if edition_data.leading_article:
            edition.leading_article=edition_data.leading_article
        if edition_data.title:
            edition.edition_title=edition_data.title        
        if edition_data.subtitle:
            edition.edition_subtitle=edition_data.subtitle        
        if edition_data.cover_url:
            edition.cover_url=edition_data.cover_url
        if edition_data.info:
            edition.info=edition_data.info.dict()
        if work:
            edition.work = work
        if illustrators:
            edition.illustrators = illustrators

        edition.hydrated = edition_data.hydrated

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
                definitive_isbn = editions_service.get_definitive_isbn(
                    edition_data.isbn
                )
            except:
                logger.warning(f"Invalid ISBN: {edition_data.isbn} - Skipping...")
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
                    first_last_to_name_key(
                        author_data.first_name, author_data.last_name
                    ),
                    author_data,
                )
            if (
                edition_data.series_name is not None
                and len(edition_data.series_name) > 0
            ):
                bulk_series_titles.add(edition_data.series_name)

        if len(bulk_author_data) > 0:
            crud.author.create_in_bulk(
                db=session, bulk_author_data_in=bulk_author_data.values()
            )
            logger.info("Authors created")

        # Series
        if len(bulk_series_titles) > 0:
            crud.work.bulk_create_series(
                session,
                bulk_series_data=bulk_series_titles,
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


    def create_new_edition(self, session: Session, edition_data: EditionCreateIn, commit=True):

        clean_isbn = editions_service.get_definitive_isbn(edition_data.isbn)
        other_isbns = editions_service.clean_isbns(edition_data.other_isbns if hasattr(edition_data, 'other_isbns') else [])
        other_isbns.discard(clean_isbn)

        # if edition already exists and is hydrated, skip. 
        # if unhydrated, gather data and hydrate at the end
        edition: Edition = self.get(session, clean_isbn)
        hydrate = False
        if edition:
            if edition.hydrated:
                logger.info("Edition already exists. Skipping...")
                return
            else:
                hydrate = True

        # collate all isbns to check if their master work exists in db
        work: Work = None
        for isbn in (list(other_isbns) + [clean_isbn]):
            master_work = crud.work.find_by_isbn(session, isbn)
            if master_work:
                work = master_work
                break

        # Get or create the authors and illustrators (some data lists the same contributor multiple times, catch them too)
        authors = [
            crud_author.get_or_create(session, author_data, commit=False)
            for author_data in edition_data.authors
        ]
        authors = list({author.id: author for author in authors}.values())
        illustrators = [
            crud_illustrator.get_or_create(session, illustrator_data, commit=False)
            for illustrator_data in edition_data.illustrators
        ]
        illustrators = list({illustrator.id: illustrator for illustrator in illustrators}.values())

        # if this is the first time we've encountered this master work, create it
        # (or get it, in the case the other_isbns list wasn't comprehensive enough to detect it earlier)
        if not work:
            work_create_data = WorkCreateIn(
                type=WorkType.BOOK,
                leading_article=edition_data.leading_article,
                title=edition_data.title,
                authors=edition_data.authors,
                # info=edition_data.info,
                series_name=edition_data.series_name,
                series_number=edition_data.series_number
            )

            work = crud_work.get_or_create(
                session, work_data=work_create_data, authors=authors, commit=False
            )
        # from now on, the master work exists.

        # create labelset if needed
        if edition_data.labelset and not edition_data.labelset.empty():
            labelset = crud.labelset.get_or_create(session, work)
            labelset = crud.labelset.patch(session, labelset, edition_data.labelset, commit=False)

        # now is a good time to link the work with any other_isbns that came along
        # with this EditionCreateIn
        logger.info(f"Discovered {len(other_isbns)} other editions under the same work")
        if other_isbns:
            logger.info(f"Associating each discovered edition with the master work")
        for isbn in other_isbns:
            other_edition = self.get_or_create_unhydrated(session, isbn)
            work.editions.append(other_edition)

        if hydrate:
            edition = self.update(
                db=session,
                edition_data=edition_data,
                work=work,
                illustrators=illustrators,
                commit=commit,
            )
        else:
            # Then, at last create the edition - raising an error if it already existed
            edition = self.create(
                db=session,
                edition_data=edition_data,
                work=work,
                illustrators=illustrators,
                commit=commit,
            )

        return edition


    def get_or_create_unhydrated(
        self, db: Session, isbn: str, commit=True
    ) -> Edition:

        edition = self.get(db, isbn)
        if not edition:
            edition = Edition(
                isbn=editions_service.get_definitive_isbn(isbn)
            )
            db.add(edition)
            if commit :
                db.commit()
            
        return edition

    # To speed up the inserts, we've opted out orm features to track each object and retrieve each pk after insertion.
    # but since we know already have the isbns, i.e the pk's that are being inserted, we can refer to them later anyway.
    # After ensuring the list is added to the db, this returns the list of cleaned pk's.
    async def create_in_bulk_unhydrated(self, session: Session, isbn_list: List[str]):
        clean_isbn_list = editions_service.clean_isbns(isbn_list)
        editions = [{"isbn": isbn} for isbn in clean_isbn_list]

        previous_count = session.execute(select(func.count(Edition.id))).scalar_one()

        if(editions):
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
