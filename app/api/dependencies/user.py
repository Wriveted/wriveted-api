import uuid

from fastapi import Depends, Path
from pydantic import BaseModel
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


class HasUserId(BaseModel):
    user_id: uuid.UUID


def get_specified_user_from_body(
    data: HasUserId,
    session: Session = Depends(get_session),
):
    return crud.user.get(db=session, id=data.user_id)


class HasReaderId(BaseModel):
    reader_id: uuid.UUID


def get_reader_from_body(
    data: HasReaderId,
    session: Session = Depends(get_session),
):
    return crud.user.get_or_404(db=session, id=data.reader_id)
