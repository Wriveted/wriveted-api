import uuid

from fastapi import Body, Depends, HTTPException, Path, Request
from fastapi_permissions import has_permission
from sqlalchemy.orm import Session

from app import crud
from app.api.dependencies.security import get_active_principals
from app.db.session import get_session


def get_user_from_id(
    user_id: uuid.UUID = Path(
        ..., description="UUID representing a unique user in the Wriveted database"
    ),
    session: Session = Depends(get_session),
):
    return crud.user.get(db=session, id=user_id)


def get_reader_from_body(
    reader_id: uuid.UUID = Body("reader_id"),
    session: Session = Depends(get_session),
):
    return crud.user.get_or_404(db=session, reader_id=reader_id)
