from fastapi import Depends, Path
from sqlalchemy.orm import Session

from app import crud
from app.db.session import get_session


def get_edition_from_isbn(
    isbn: str = Path(..., description="ISBN string representing a unique edition"),
    session: Session = Depends(get_session),
):
    return crud.edition.get_or_404(db=session, id=isbn)
