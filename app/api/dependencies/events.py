from fastapi import Depends, HTTPException, Path
from sqlalchemy.orm import Session
from app.api.dependencies.security import get_current_active_user

from app.db.session import get_session
from app import crud
from app.models.supporter_reader_association import SupporterReaderAssociation
from app.models.user import User
from app.permissions import Permission
from starlette import status


def get_event_by_id(
    event_id: str = Path(..., description="UUID string representing a unique event"),
    session: Session = Depends(get_session),
):
    return crud.event.get_or_404(db=session, id=event_id)


def get_and_validate_reading_log_event_by_id(
    event=Permission("read", get_event_by_id),
    supporter: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    if not event.title.startswith("Reader timeline event:"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The event is not a reading log event",
        )

    reader = crud.user.get_or_404(db=session, id=event.user_id)

    # check if the supporter is -actively- associated with the reader
    if (
        session.query(SupporterReaderAssociation)
        .filter(SupporterReaderAssociation.reader_id == reader.id)
        .filter(SupporterReaderAssociation.supporter_id == supporter.id)
        .filter(SupporterReaderAssociation.is_active == True)
        .one_or_none()
    ) is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Supporter not currently associated with reader",
        )

    # check if feedback for the event has already been submitted by this supporter
    if crud.event.get_all_with_optional_filters(
        session,
        query_string="Supporter encouragement: Reading feedback sent",
        user=supporter,
        info_jsonpath_match=f'($.event_id == "{event.id}")',
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Feedback already submitted for this reading log event",
        )

    return event
