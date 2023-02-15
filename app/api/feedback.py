from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette import status
from structlog import get_logger
from app import crud
from app.api.dependencies.security import (
    ReaderFeedbackOtpData,
    validate_and_decode_reader_feedback_otp,
)
from app.db.session import get_session
from app.models.collection_item import CollectionItem
from app.models.event import EventLevel
from app.schemas.events.event import EventCreateIn
from app.schemas.events.special_events import ReadingLogEvent
from app.schemas.feedback import ReadingLogEventDetail, ReadingLogEventFeedback

logger = get_logger()

router = APIRouter(
    tags=["Feedback"],
)


@router.get(
    "/reader-feedback/{otp}",
    response_model=ReadingLogEventDetail,
    include_in_schema=False,
)
async def validate(
    data: ReaderFeedbackOtpData = Depends(validate_and_decode_reader_feedback_otp),
    session: Session = Depends(get_session),
):
    """
    Validate an encoded reader-feedback OTP, returning the reading log event details if valid.
    """

    # ---check for event integrity---
    event = crud.event.get_or_404(session, data.event_id)

    reader = crud.user.get_or_404(session, event.user_id)

    item: CollectionItem = crud.collection.get_collection_item_or_404(
        session, collection_item_id=event.info.get("collection_item_id")
    )

    reading_logged: ReadingLogEvent = event.info.get("reading_logged")
    if not reading_logged:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event does not have reading_logged info",
        )
    # --------------------

    feedback_key = f"{data.event_id}_{data.email or data.phone}"
    if crud.event.get_all_with_optional_filters(
        session,
        query_string="Reading Log Feedback: Submitted",
        user=reader,
        info_jsonpath_match=f'($.feedback_key == "{feedback_key}")',
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Feedback already submitted for this reading log event",
        )

    return ReadingLogEventDetail(
        reader_name=reader.name,
        book_title=item.get_display_title(),
        cover_url=item.edition.cover_url or item.info.get("cover_image"),
        **reading_logged.dict(),
    )


@router.post(
    "/reader-feedback/{otp}",
    include_in_schema=False,
)
async def submit(
    feedback: ReadingLogEventFeedback,
    otp: ReaderFeedbackOtpData = Depends(validate_and_decode_reader_feedback_otp),
    session: Session = Depends(get_session),
):
    reading_logged_event = crud.event.get(session, otp.event_id)
    if not reading_logged_event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    reader = crud.user.get(session, reading_logged_event.user_id)
    item = crud.collection.get_collection_item_or_404(
        session, reading_logged_event.info.get("reading_logged").collection_item_id
    )

    feedback_key = f"{otp.event_id}_{otp.email or otp.phone}"
    if crud.event.get_all_with_optional_filters(
        session,
        query_string="Reading Log Feedback: Submitted",
        user=reader,
        info_jsonpath_match=f'($.feedback_key == "{feedback_key}")',
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Feedback already submitted for this reading log event",
        )

    feedback_event_data = EventCreateIn(
        title="Reading Log Feedback: Submitted",
        description=f"A friend or family member of {reader.name} submitted feedback for their logged reading of {item.get_display_title()}.",
        level=EventLevel.NORMAL,
        user_id=reader.id,
        info={
            "collection_item_id": item.id,
            "feedback_key": feedback_key,
            "nickname": otp.nickname,
            "source": "email" if otp.email else "phone",
            "feedback": feedback.dict(),
        },
    )
    crud.event.create(session, obj_in=feedback_event_data)
