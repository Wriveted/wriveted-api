import uuid

from fastapi import Depends, Path
from sqlalchemy.orm import Session

from app import crud
from app.db.session import get_session


def get_user_from_id(
    user_id: uuid.UUID = Path(
        ..., description="UUID representing a unique user in the Wriveted database"
    ),
    session: Session = Depends(get_session),
):
    return crud.user.get(db=session, id=user_id)
