import uuid

from fastapi import Path, Depends
from sqlalchemy.orm import Session

from app import crud
from app.db.session import get_session


def get_school_from_wriveted_id(
    wriveted_identifier: uuid.UUID = Path(
        ..., description="UUID representing a unique school in the Wriveted database"
    ),
    session: Session = Depends(get_session),
):
    return crud.school.get_by_wriveted_id_or_404(
        db=session, wriveted_id=wriveted_identifier
    )


def get_school_from_raw_id(
    id: str = Path(..., description="Raw sql integer id for school object"),
    session: Session = Depends(get_session),
):
    return crud.school.get_by_id_or_404(db=session, id=id)
