from typing import TYPE_CHECKING, Optional, Union

if TYPE_CHECKING:
    from app.services.event_outbox_service import EventPriority

from pydantic import ValidationError
from sqlalchemy.orm import Session
from structlog import get_logger

from app import crud
from app.config import get_settings
from app.db.session import get_session_maker
from app.models import Event, School
from app.models.booklist import ListType
from app.models.collection_item import CollectionItem
from app.models.collection_item_activity import CollectionItemReadStatus
from app.models.event import EventLevel, EventSlackChannel
from app.models.service_account import ServiceAccount
from app.models.user import User, UserAccountType
from app.repositories.booklist_repository import booklist_repository
from app.repositories.collection_item_activity_repository import (
    collection_item_activity_repository,
)
from app.repositories.edition_repository import edition_repository
from app.schemas.booklist import (
    BookListCreateIn,
    BookListItemInfo,
    BookListItemUpdateIn,
    BookListUpdateIn,
    ItemUpdateType,
)
from app.schemas.collection import CollectionItemActivityBase
from app.schemas.events.huey_events import HueyBookReviewedInfo
from app.schemas.events.special_events import ReadingLogEvent
from app.schemas.feedback import ReadingLogEventFeedback
from app.services.feedback import process_reader_feedback_alerts

# NOTE: Slack SDK imports removed - now handled by SlackNotificationService
from app.services.slack_notification import send_slack_alert_reliable_sync

# EventPriority imported in TYPE_CHECKING block above

logger = get_logger()
config = get_settings()

# NOTE: event_level_emoji moved to SlackNotificationService.EVENT_LEVEL_EMOJI


# NOTE: _parse_event_to_slack_message function removed - replaced by SlackNotificationService._format_event_for_slack


def handle_event_to_slack_alert(
    session: Session,
    event_id: str,
    slack_channel: EventSlackChannel,
    extra: dict = None,
):
    """
    Send Slack alert using the new SlackNotificationService.

    This function maintains backward compatibility while using the new
    service layer architecture with Event Outbox pattern for reliable delivery.
    """
    from app.services.event_outbox_service import EventPriority

    try:
        # Use the new service with reliable delivery via Event Outbox
        send_slack_alert_reliable_sync(
            db=session,
            event_id=event_id,
            slack_channel=slack_channel,
            extra=extra,
            priority=EventPriority.NORMAL,
        )
        logger.debug("Slack alert queued successfully via SlackNotificationService")
    except Exception as e:
        logger.error(
            "Error queuing Slack alert via service layer",
            event_id=event_id,
            slack_channel=slack_channel.value,
            error=str(e),
        )


def create_event(
    session: Session,
    title: str,
    description: str = None,
    info: dict = None,
    level: EventLevel = EventLevel.NORMAL,
    slack_channel: EventSlackChannel | None = None,
    slack_extra: dict = None,
    school: School = None,
    account: Optional[Union[ServiceAccount, User]] = None,
    commit: bool = True,
    # New unified workflow parameters
    enable_processing: bool = True,  # Whether to trigger event processing
    external_notifications: bool = None,  # Auto-detected if None
) -> Event:
    """
    Create a new business event with unified workflow for external notifications.

    This is the single entry point for all business event creation. It:
    1. Creates the business event record (audit trail)
    2. Automatically dispatches to EventOutbox for external notifications
    3. Handles both Slack alerts and general event processing

    Args:
        session: Database session
        title: Event title (used for processing logic)
        description: Human-readable description
        info: Additional event data
        level: Event severity level
        slack_channel: If provided, queues reliable Slack notification
        slack_extra: Additional data for Slack message
        school: Associated school
        account: User or service account
        commit: Whether to commit the transaction
        enable_processing: Whether to enable background event processing
        external_notifications: Force enable/disable external notifications

    Returns:
        The created Event object
    """
    from app.services.event_outbox_service import EventOutboxService, EventPriority

    # Step 1: Create business event (audit trail)
    event = crud.event.create(
        session,
        title=title,
        description=description,
        info=info,
        level=level,
        school=school,
        account=account,
        commit=False,  # We'll handle commit after outbox dispatch
    )

    # Flush to get the event ID for EventOutbox dispatch
    session.flush()

    # Step 2: Determine if external notifications are needed
    if external_notifications is None:
        # Auto-detect based on parameters and event characteristics
        external_notifications = (
            slack_channel is not None
            or _requires_external_notification(title, level)
            or enable_processing
        )

    # Step 3: Dispatch to EventOutbox for reliable delivery (if needed)
    if external_notifications:
        outbox_service = EventOutboxService()

        # Handle Slack notification via SlackNotificationService (replaces direct EventOutbox)
        if slack_channel is not None:
            # Determine priority based on event level
            priority = _get_event_priority(level)

            # Use the new service layer for reliable Slack delivery
            send_slack_alert_reliable_sync(
                db=session,
                event_id=str(event.id),
                slack_channel=slack_channel,
                extra=slack_extra,
                priority=priority,
            )

            logger.info(
                "Slack notification queued via SlackNotificationService",
                event_id=event.id,
                slack_channel=slack_channel.value,
                priority=priority.value,
            )

        # Handle general event processing via EventOutbox (replaces direct queue_background_task)
        if enable_processing and _requires_background_processing(title):
            processing_payload = {
                "event_id": str(event.id),
                "title": title,
                "info": info or {},
            }

            outbox_service.publish_event_sync(
                db=session,
                event_type="event_processing",
                destination="internal:process-event",
                payload=processing_payload,
                priority=EventPriority.NORMAL,
                routing_key="processing",
                headers={"event_title": title, "requires_processing": "true"},
                max_retries=3,
                user_id=getattr(account, "id", None)
                if hasattr(account, "id")
                else None,
            )

            logger.info(
                "Event processing queued via EventOutbox",
                event_id=event.id,
                event_title=title,
            )

    # Step 4: Commit transaction
    if commit:
        session.commit()
        session.refresh(event)

    logger.info(
        "Business event created",
        event_id=event.id,
        title=title,
        level=level.value,
        external_notifications=external_notifications,
    )

    return event


def _requires_external_notification(title: str, level: EventLevel) -> bool:
    """Determine if an event type requires external notifications."""
    # High severity events should always notify
    if level in [EventLevel.ERROR, EventLevel.WARNING]:
        return True

    # Specific event types that should notify external systems
    notification_events = [
        "User created",
        "Subscription started",
        "Subscription cancelled",
        "Payment failed",
        "System error",
    ]

    return title in notification_events


def _requires_background_processing(title: str) -> bool:
    """Determine if an event type requires background processing."""
    # Events that need background processing
    processing_events = [
        "Huey: Book reviewed",
        "Reader timeline event: Reading logged",
        "Subscription started",
        "Test",  # Keep for testing
    ]

    return title in processing_events


def _get_event_priority(level: EventLevel) -> "EventPriority":
    """Map event level to EventOutbox priority."""
    from app.services.event_outbox_service import EventPriority

    priority_map = {
        EventLevel.DEBUG: EventPriority.LOW,
        EventLevel.NORMAL: EventPriority.NORMAL,
        EventLevel.WARNING: EventPriority.HIGH,
        EventLevel.ERROR: EventPriority.CRITICAL,
    }
    return priority_map.get(level, EventPriority.NORMAL)


def process_events(event_id):
    logger.info("Background processing")
    Session = get_session_maker()
    with Session() as session:
        event = crud.event.get(session, id=event_id)
        logger.warning(
            "Background processing event", type=event.title, event_id=event.id
        )
        if event.title == "Huey: Book reviewed":
            return process_book_review_event(session, event)
        elif event.title == "Test":
            logger.info("Changing event", e=event)
            event.info["description"] = "MODIFIED"
            session.commit()
            session.refresh(event)
            logger.info("Changed", e=event)
            return {"msg": "ok"}
        elif event.title == "Reader timeline event: Reading logged":
            return process_reading_logged_event(session, event)
        elif event.title == "Subscription started":
            return process_subscription_started_event(session, event)
        # elif event.title == "Supporter encouragement: Achievement feedback sent":
        #     # e.g. "Well done for reading 10 books this year!"
        #     # (not for a specific reading event, but for a milestone or other automated achievement)
        #     return process_supporter_achievement_feedback_event(session, event)
        else:
            return


def process_subscription_started_event(session: Session, event: Event):
    """ """

    logger.info("Placeholder to process subscription started event", info=event.info)


def process_book_review_event(session: Session, event: Event):
    """
    Add liked books to booklists for optional school, class and user.

    Creates the booklists if they don't exist.
    """
    logger.info("Processing book review event")

    logger.debug("First we prepare a list of the liked books")
    liked_items = get_liked_books_from_book_review_event(session, event)

    if len(liked_items) == 0:
        logger.info("No liked books")
        return

    logger.info(f"Review included {len(liked_items)} liked books")

    # Work out if this review event is associated with a school
    if event.school is None:
        logger.debug("No school associated with book review")
    else:
        booklist = update_or_create_liked_books(
            session,
            liked_items,
            booklist_type=ListType.SCHOOL,
            school=event.school,
            user=event.user,
        )
        logger.info("Updated school booklist", booklist=booklist)

    if event.user is None:
        logger.debug("No user associated with book review")
    else:
        logger.debug("Updating personal list of liked books", user=event.user)
        personal_booklist = update_or_create_liked_books(
            session,
            liked_items,
            booklist_type=ListType.PERSONAL,
            school=None,
            user=event.user,
        )
        logger.info("Updated personal liked books", booklist=personal_booklist)

        if event.user.type == UserAccountType.STUDENT:
            class_group = event.user.class_group
            logger.debug("Updating class list of liked books", class_group=class_group)
            class_booklist = update_or_create_liked_books(
                session,
                liked_items,
                booklist_type=ListType.SCHOOL,
                school=event.school,
                user=event.user,
                booklist_name=f"{class_group.name} Liked Books",
            )
            logger.info("Updated class liked books", booklist=class_booklist)


def process_reading_logged_event(session: Session, event: Event):
    """
    Process a reading logged event, creating a CollectionItemActivity of the appropriate status, and optionally alert the reader's parent.
    """
    logger.info("Processing reading logged event")

    try:
        log_data = ReadingLogEvent.model_validate(event.info)
    except ValidationError as e:
        logger.warning("Error parsing reading logged event", error=e, event=event)
        return

    status = CollectionItemReadStatus.READING
    if log_data.stopped:
        logger.info("Reading logged as stopped")
        status = CollectionItemReadStatus.STOPPED_READING
    if log_data.finished:
        logger.info("Reading logged as finished")
        status = CollectionItemReadStatus.READ

    activity = CollectionItemActivityBase(
        collection_item_id=log_data.collection_item_id,
        reader_id=event.user_id,
        status=status,
    )
    collection_item_activity_repository.create(session, obj_in=activity)

    item: CollectionItem = crud.collection.get_collection_item(
        db=session, collection_item_id=log_data.collection_item_id
    )

    if reader := crud.user.get(session, id=event.user_id):
        process_reader_feedback_alerts(session, reader, item, event, log_data)


def process_supporter_reading_feedback_event(session: Session, event: Event):
    """
    Process a supporter feedback event
    """
    logger.info("Processing supporter feedback event")

    try:
        feedback_data = ReadingLogEventFeedback.model_validate(event.info)
    except ValidationError as e:
        logger.warning("Error parsing supporter feedback event", error=e, event=event)
        return

    log_event = crud.event.get(session, id=feedback_data.event_id)
    if log_event is None:
        logger.warning("Log event not found", event_id=feedback_data.event_id)
        return

    item = crud.collection.get_collection_item_or_404(
        db=session, collection_item_id=log_event.info.get("collection_item_id")
    )

    # event is good, create a "notification" event for the reader
    crud.event.create(
        session,
        title="Notification: Supporter left feedback",
        description=f"Reader {log_event.user.name} received encouragement from {event.user.name}",
        info={
            "title": f"{event.user.name} sent you a message!",
            "extra": {
                "image": item.edition.cover_url or item.info.get("cover_image"),
                "message": f"For reading {item.edition.title or item.info.get('title')}",
            },
            **feedback_data.dict(),
        },
        account=log_event.user,
    )


def update_or_create_liked_books(
    session: Session,
    liked_items: list[BookListItemUpdateIn],
    booklist_type: str,
    school: Optional[School],
    user: Optional[User],
    booklist_name="Liked Books",
):
    # See if the "Liked Books" booklist exists.
    liked_booklist_query = booklist_repository.get_all_query_with_optional_filters(
        db=session,
        list_type=booklist_type,
        school=school,
        user=user,
        query_string=booklist_name,
    )
    booklist = session.scalars(liked_booklist_query).first()
    if booklist is None:
        logger.info("Creating a new booklist", type=booklist_type)
        booklist = booklist_repository.create(
            db=session,
            obj_in=BookListCreateIn(
                name=booklist_name,
                type=booklist_type,
                user_id=user.id if user is not None else None,
                school_id=school.id if school is not None else None,
                info={"description": "List of all books liked in a Chat"},
            ),
        )

    # Update with any newly liked items. Existing likes will be skipped
    logger.info("Updating booklist", booklist_id=booklist.id)
    booklist = booklist_repository.update(
        db=session, db_obj=booklist, obj_in=BookListUpdateIn(items=liked_items)
    )
    return booklist


def get_liked_books_from_book_review_event(
    session: Session, event: Event
) -> list[BookListItemUpdateIn]:
    liked_items = []
    logger.info("Getting liked books from event", event_info=event.info)

    if "reviews" in event.info:
        logger.warning("Unexpected event schema. Processing multiple reviews")
        for review in event.info["reviews"]:
            logger.debug("Processing review", raw_review=review)
            isbn = review["isbn"]
            book_liked = review["liked"]
            liked_booklist_item = booklist_item_update_from_isbn(
                session, isbn, book_liked
            )
            if liked_booklist_item:
                liked_items.append(liked_booklist_item)

    else:
        info: HueyBookReviewedInfo = HueyBookReviewedInfo.model_validate(event.info)
        logger.debug("Processing a book review", raw_review=info)
        liked_booklist_item = booklist_item_update_from_isbn(
            session, info.isbn, info.liked
        )
        if liked_booklist_item:
            liked_items.append(liked_booklist_item)

    return liked_items


def booklist_item_update_from_isbn(
    session, isbn, book_liked
) -> Optional[BookListItemUpdateIn]:
    edition = edition_repository.get(db=session, id=isbn)
    if edition and book_liked:
        liked_booklist_item = BookListItemUpdateIn(
            action=ItemUpdateType.ADD,
            work_id=edition.work_id,
            info=BookListItemInfo(
                edition=isbn,
            ),
        )
        return liked_booklist_item
