import uuid

from fastapi import Depends, Path, Query
from sqlalchemy.orm import Session

from app import crud
from app.db.session import get_session


def get_school_from_wriveted_id(
    wriveted_identifier: uuid.UUID = Path(
        ..., description="UUID representing a unique school in the Wriveted database"
    ),
    db: Session = Depends(get_session),
):
    with db as session:
        return crud.school.get_by_wriveted_id_or_404(
            db=session, wriveted_id=wriveted_identifier
        )


def get_optional_school_from_wriveted_id_query(
    wriveted_identifier: uuid.UUID = Query(
        None, description="UUID representing a unique school in the Wriveted database"
    ),
    session: Session = Depends(get_session),
):
    if wriveted_identifier is None:
        return None
    else:
        return crud.school.get_by_wriveted_id_or_404(
            db=session, wriveted_id=wriveted_identifier
        )
