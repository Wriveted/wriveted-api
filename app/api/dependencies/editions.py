from fastapi import Depends, Path
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.repositories.edition_repository import edition_repository
from app.services.editions import get_definitive_isbn


def get_edition_from_isbn(
    isbn: str = Path(..., description="ISBN string representing a unique edition"),
    session: Session = Depends(get_session),
):
    return edition_repository.get_or_404(db=session, isbn=get_definitive_isbn(isbn))
