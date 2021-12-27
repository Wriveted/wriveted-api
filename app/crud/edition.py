from typing import Any, List

from sqlalchemy import select
from sqlalchemy.orm import Session, Query

from app.crud import CRUDBase
from app.models import Edition, Work, Author, Illustrator
from app.schemas.edition import EditionCreateIn


class CRUDEdition(CRUDBase[Edition, Any, Any]):
    """
    We use ISBN in the CRUD layer instead of the database ID
    """

    def get_query(self, db: Session, id: Any) -> Query:
        return select(Edition).where(Edition.ISBN == id)

    def create(self,
               db: Session,
               edition_data: EditionCreateIn,
               work: Work,
               illustrators: List[Illustrator],
               commit=True) -> Edition:
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
