import uuid

from fastapi import Depends, HTTPException, Path
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import crud
from app.db.session import get_session
from app.models.booklist import BookList, ListSharingType, ListType


def get_booklist_from_wriveted_id(
    booklist_identifier: uuid.UUID = Path(
        ..., description="UUID representing a unique list of books"
    ),
    session: Session = Depends(get_session),
):
    return crud.booklist.get_or_404(db=session, id=booklist_identifier)


def get_public_huey_booklist_from_slug(
    booklist_slug: str = Path(
        ..., description="Slug representing a public Huey booklist/pseudoarticle"
    ),
    session: Session = Depends(get_session),
):
    booklist = session.scalars(
        select(BookList).filter(BookList.slug == booklist_slug)
    ).one_or_none()
    # obscure the 404 if the booklist exists but is not public
    if booklist is None or booklist.sharing != ListSharingType.PUBLIC:
        raise HTTPException(
            status_code=404,
            detail="Booklist not found",
        )
    if booklist.type != ListType.HUEY:
        raise HTTPException(
            status_code=403,
            detail="Booklist is not a public Huey booklist",
        )
    return booklist
