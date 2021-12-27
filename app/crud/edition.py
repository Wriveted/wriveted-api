from typing import Any, List

from sqlalchemy import select
from sqlalchemy.orm import Session, Query

from app.crud import CRUDBase
from app.crud.author import author as crud_author
from app.crud.work import work as crud_work
from app.crud.illustrator import illustrator as crud_illustrator

from app.models import Edition, Work, Illustrator
from app.models.work import WorkType
from app.schemas.edition import EditionCreateIn
from app.schemas.work import WorkCreateIn


class CRUDEdition(CRUDBase[Edition, Any, Any]):
    """
    We use ISBN in the CRUD layer instead of the database ID
    """

    def get_query(self, db: Session, id: Any) -> Query:
        return select(Edition).where(Edition.ISBN == id)

    def get_multi_query(self, db: Session, ids: List[Any], *, order_by=None) -> Query:
        return self.get_all_query(db, order_by=order_by).where(Edition.ISBN.in_(ids))

    def create(self,
               db: Session,
               edition_data: EditionCreateIn,
               work: Work,
               illustrators: List[Illustrator],
               commit=True) -> Edition:
        """
        Insert an edition row in the table assuming the related objects exist.

        See `create_new_edition` to also get_or_create the related Author/Work/Illustrator
        objects.
        """
        edition = Edition(
            edition_title=edition_data.title,
            ISBN=edition_data.ISBN,
            cover_url=edition_data.cover_url,
            info=edition_data.info,
            work=work,
            illustrators=illustrators
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

        editions = [
            self.create_new_edition(session, edition_data, commit=True)
            for edition_data in bulk_edition_data
        ]
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
            title=edition_data.work_title if edition_data.work_title is not None else edition_data.title,
            authors=edition_data.authors,
            info=edition_data.info,
            series_title=edition_data.series_title,
        )

        work = crud_work.get_or_create(
            session,
            work_data=work_create_data,
            authors=authors,
            commit=False
        )
        # Get or create the illustrators
        illustrators = [
            crud_illustrator.get_or_create(
                session,
                illustrator_data,
                commit=False
            )
            for illustrator_data in edition_data.illustrators
        ]
        # Then, at last create the edition - raising an error if it already existed
        edition = self.create(
            db=session,
            edition_data=edition_data,
            work=work,
            illustrators=illustrators,
            commit=commit
        )
        return edition


edition = CRUDEdition(Edition)
