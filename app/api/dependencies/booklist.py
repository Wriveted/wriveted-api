import uuid

from fastapi import Path, Depends, Query
from sqlalchemy.orm import Session

from app import crud
from app.db.session import get_session


def get_booklist_from_wriveted_id(
    booklist_identifier: uuid.UUID = Path(
        ..., description="UUID representing a unique list of books"
    ),
    session: Session = Depends(get_session),
):
    return crud.booklist.get_or_404(db=session, id=booklist_identifier)
