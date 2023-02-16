from fastapi import APIRouter, Depends, Security
from sqlalchemy.orm import Session
from structlog import get_logger

from app import crud
from app.api.dependencies.events import (
    get_and_validate_reading_log_event_by_id,
)
from app.api.dependencies.security import (
    get_current_active_supporter,
)
from app.db.session import get_session
from app.models.event import Event, EventLevel
from app.models.parent import Parent
from app.models.supporter import Supporter
from app.schemas.events.event import EventCreateIn
from app.schemas.events.event_detail import EventDetail
from app.schemas.feedback import ReadingLogEventDetail, ReadingLogEventFeedback

logger = get_logger()

router = APIRouter(
    tags=["Supporters"],
    dependencies=[Security(get_current_active_supporter)],
)


@router.get("/supporters/event/{event_id}", response_model=ReadingLogEventDetail)
async def get_reading_log_event_for_support(
    event: Event = Depends(get_and_validate_reading_log_event_by_id),
    session: Session = Depends(get_session),
):
    reader = event.user
    item = crud.item.get_or_404(db=session, id=event.info["item_id"])

    return ReadingLogEventDetail(
        reader_name=reader.name,
        book_title=item.get_display_title(),
        cover_url=item.edition.cover_url or item.info.get("cover_image"),
        **event.info.dict(),
    )


@router.post("/supporters/event/{event_id}", response_model=EventDetail)
async def submit_reader_feedback(
    feedback: ReadingLogEventFeedback,
    event: Event = Depends(get_and_validate_reading_log_event_by_id),
    supporter: Parent | Supporter = Depends(get_current_active_supporter),
    session: Session = Depends(get_session),
):
    event_data = EventCreateIn(
        title="Supporter encouragement: Reading feedback sent",
        description=f"Supporter {supporter.name} sent feedback to reader {event.user.name}",
        level=EventLevel.NORMAL,
        user_id=event.user_id,
        info=feedback.dict(),
    )
    event = crud.event.create(db=session, obj_in=event_data)
    return event
