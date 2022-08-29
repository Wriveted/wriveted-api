import uuid

from fastapi import Depends, Path
from sqlalchemy.orm import Session

from app import crud
from app.db.session import get_read_only_session
from app.models.class_group import ClassGroup


def get_class_from_id(
    id: uuid.UUID = Path(
        ..., description="UUID representing a unique class in the Wriveted database"
    ),
    session: Session = Depends(get_read_only_session),
):
    return crud.class_group.get_or_404(db=session, id=id)


def get_school_from_class_id(
    class_orm: ClassGroup = Depends(get_class_from_id),
):
    return class_orm.school
