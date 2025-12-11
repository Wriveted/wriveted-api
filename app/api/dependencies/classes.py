import uuid

from fastapi import Depends, Path
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.models.class_group import ClassGroup
from app.repositories.class_group_repository import class_group_repository


def get_class_from_id(
    id: uuid.UUID = Path(
        ..., description="UUID representing a unique class in the Wriveted database"
    ),
    session: Session = Depends(get_session),
):
    return class_group_repository.get_or_404(db=session, class_group_id=id)


def get_school_from_class_id(
    class_orm: ClassGroup = Depends(get_class_from_id),
):
    return class_orm.school
