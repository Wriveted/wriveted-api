from fastapi import APIRouter, Depends, Security
from sqlalchemy.orm import Session
from structlog import get_logger

from app import crud
from app.api.dependencies.events import (
    get_and_validate_reading_log_event_by_id,
)
from app.api.dependencies.security import (
    get_current_active_user,
)
from app.db.session import get_session
from app.models.event import Event, EventLevel
from app.models.supporter_reader_association import SupporterReaderAssociation
from app.models.user import User
from app.schemas.events.event_detail import EventDetail
from app.schemas.feedback import ReadingLogEventDetail, ReadingLogEventFeedback

logger = get_logger()

router = APIRouter(
    tags=["Supporters"],
    dependencies=[Security(get_current_active_user)],
)


@router.get("/feedback/{event_id}", response_model=ReadingLogEventDetail)
async def get_reading_log_event_for_support(
    event: Event = Depends(get_and_validate_reading_log_event_by_id),
    supporter: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    reader = event.user
    item = crud.collection.get_collection_item_or_404(
        db=session, collection_item_id=event.info.get("collection_item_id")
    )

    reader_association = supporter.supportee_associations.filter(
        SupporterReaderAssociation.reader_id == reader.id
    ).first()

    return ReadingLogEventDetail(
        reader_name=reader.name,
        supporter_nickname=reader_association.supporter_nickname,
        book_title=item.get_display_title(),
        cover_url=item.get_cover_url(),
        **event.info,
    )


@router.post("/feedback/{event_id}", response_model=EventDetail)
async def submit_reader_feedback(
    feedback: ReadingLogEventFeedback,
    event: Event = Depends(get_and_validate_reading_log_event_by_id),
    supporter: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    info = feedback.dict()
    info["supporter_id"] = str(supporter.id)
    info["targeted_event_id"] = str(event.id)
    crud.event.create(
        session=session,
        title="Supporter encouragement: Reading feedback sent",
        description=f"Supporter {supporter.name} sent feedback to reader {event.user.name}",
        level=EventLevel.NORMAL,
        account=supporter,
        info=info,
    )

    # create a "notification" event for the reader
    item = crud.collection.get_collection_item_or_404(
        db=session, collection_item_id=event.info.get("collection_item_id")
    )

    reader_association = supporter.supportee_associations.filter(
        SupporterReaderAssociation.reader_id == event.user.id
    ).first()

    return crud.event.create(
        session,
        title="Notification: Supporter left feedback",
        description=f"Reader {event.user.name} received encouragement from {supporter.name}",
        level=EventLevel.NORMAL,
        info={
            "event_id": str(event.id),
            "notification_title": f"{reader_association.supporter_nickname} sent you a message!",
            "notification_type": "supporter_feedback",
            "notification_extra": {
                "image": item.get_cover_url(),
                "message": f"For reading {item.get_display_title()}",
            },
            "notification_body_text": feedback.comment,
            "notification_body_image": feedback.gif_url,
            "notification_from_name": reader_association.supporter_nickname,
        },
        account=event.user,
    )
