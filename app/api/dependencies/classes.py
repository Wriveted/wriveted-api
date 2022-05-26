import uuid

from fastapi import Depends, Path
from sqlalchemy.orm import Session

from app import crud
from app.db.session import get_session
from app.models import School


def get_class_from_wriveted_id(
    wriveted_identifier: uuid.UUID = Path(
        ..., description="UUID representing a unique class in the Wriveted database"
    ),
    session: Session = Depends(get_session),
):
    return crud.classes.get_by_wriveted_id_or_404(
        db=session, wriveted_id=wriveted_identifier
    )


def get_school_from_class_wriveted_id(
    class_orm: ClassGroup = Depends(get_class_from_wriveted_id),
):
    return class_orm.school
