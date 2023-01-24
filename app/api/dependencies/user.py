from uuid import UUID

from fastapi import Depends, Path
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import crud
from app.db.session import get_session


def get_user_from_id(
    user_id: UUID = Path(
        ..., description="UUID representing a unique user in the Wriveted database"
    ),
    session: Session = Depends(get_session),
):
    return crud.user.get(db=session, id=user_id)


class MaybeHasUserId(BaseModel):
    user_id: UUID | None


def get_optional_specified_user_from_body(
    data: MaybeHasUserId,
    session: Session = Depends(get_session),
):
    return crud.user.get_or_404(db=session, id=data.user_id) if data.user_id else None


class HasReaderId(BaseModel):
    reader_id: UUID


def get_reader_from_body(
    data: HasReaderId,
    session: Session = Depends(get_session),
):
    return crud.user.get_or_404(db=session, id=data.reader_id)
