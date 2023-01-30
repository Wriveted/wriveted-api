import json
from typing import Optional, Union
from pydantic import ValidationError

from sqlalchemy.orm import Session
from structlog import get_logger

from app import crud
from app.config import get_settings
from app.db.session import get_session_maker
from app.models import Event, School
from app.models.booklist import ListType
from app.models.collection_item import CollectionItem
from app.models.collection_item_activity import (
    CollectionItemActivity,
    CollectionItemReadStatus,
)
from app.models.event import EventLevel, EventSlackChannel
from app.models.reader import Reader
from app.models.service_account import ServiceAccount
from app.models.user import User, UserAccountType
from app.schemas.booklist import (
    BookListCreateIn,
    BookListItemInfo,
    BookListItemUpdateIn,
    BookListUpdateIn,
    ItemUpdateType,
)
from app.schemas.collection import CollectionItemActivityBase
from app.schemas.events.special_events import ReadingLogEvent
from app.services.background_tasks import queue_background_task
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = get_logger()
config = get_settings()

event_level_emoji = {
    EventLevel.DEBUG: ":bug:",
    EventLevel.NORMAL: ":information_source:",
    EventLevel.WARNING: ":warning:",
    EventLevel.ERROR: ":bangbang:",
}


def _parse_event_to_slack_message(event: Event, extra: dict = None) -> str:
    """
    Parse an event into a Slack message using the Block Kit format.
    """
    blocks = []
    text = f"{event_level_emoji[event.level]} API Event: *{event.title}* \n{event.description}"

    blocks.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": text,
            },
        }
    )
    fields = []
    if event.school is not None:
        fields.append(
            {
                "type": "mrkdwn",
                "text": f"*School*: <https://api.wriveted.com/school/{event.school.wriveted_identifier}|{event.school.name}>",
            }
        )
    if event.user is not None:
        fields.append(
            {
                "type": "mrkdwn",
                "text": f"*User*: <https://api.wriveted.com/user/{event.user_id}|{event.user.name}>",
            }
        )
    if event.service_account is not None:
        fields.append(
            {
                "type": "mrkdwn",
                "text": f"*Service Account*: {event.service_account.name}",
            }
        )
    if len(fields) > 0:
        blocks.append({"type": "section", "fields": fields})

    if event.info:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Info*:",
                },
            }
        )
        info_fields = []
        for key, value in event.info.items():
            if key != "description":
                info_fields.append({"type": "mrkdwn", "text": f"*{key}*: {str(value)}"})
        blocks.append({"type": "section", "fields": info_fields})

    if extra:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Extra*:",
                },
            }
        )
        extra_fields = []
        for key, value in extra.items():
            extra_fields.append({"type": "mrkdwn", "text": f"*{key}*: {str(value)}"})
        blocks.append({"type": "section", "fields": extra_fields})

    output = json.dumps(blocks)
    return (output, text)


def handle_event_to_slack_alert(
    session: Session,
    event_id: int,
    slack_channel: EventSlackChannel,
    extra: dict = None,
):
    event = crud.event.get(session, id=event_id)
    payload, text = _parse_event_to_slack_message(event, extra=extra)
    logger.info(
        "Sending event to Slack",
        title=event.title,
        description=event.description,
        channel=slack_channel,
        token=config.SLACK_BOT_TOKEN,
    )

    client = WebClient(token=config.SLACK_BOT_TOKEN)
    try:
        _response = client.chat_postMessage(
            channel=slack_channel, blocks=payload, text=text
        )
        logger.info("Slack alert posted successfully")
    except SlackApiError as e:
        logger.error("Error sending Slack alert: {}".format(e))


def create_event(
    session: Session,
    title: str,
    description: str = None,
    info: dict = None,
    level: EventLevel = EventLevel.NORMAL,
    slack_channel: EventSlackChannel | None = None,
    slack_extra: dict = None,
    school: School = None,
    account: Union[ServiceAccount, User] = None,
    commit: bool = True,
) -> Event:
    """
    Create a new event, passing a Slack alert if requested.
    """
    event = crud.event.create(
        session,
        title=title,
        description=description,
        info=info,
        level=level,
        school=school,
        account=account,
        commit=commit,
    )

    if slack_channel is not None:
        queue_background_task(
            "event-to-slack-alert",
            {
                "event_id": str(event.id),
                "slack_channel": slack_channel,
                "slack_extra": slack_extra,
            },
        )

    return event


def process_events(event_id):
    Session = get_session_maker()
    with Session() as session:
        event = crud.event.get(session, id=event_id)
        logger.warning(
            "Background processing event", type=event.title, event_id=event.id
        )
        match event.title:
            case "Huey: Book reviewed":
                return process_book_review_event(session, event)
            case "Test":
                logger.info("Changing event", e=event)
                event.info["description"] = "MODIFIED"
                session.commit()
                session.refresh(event)
                logger.info("Changed", e=event)
                return {"msg": "ok"}
            case "Reader timeline event: Reading logged":
                return process_reading_logged_event(session, event)
            case _:
                return


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
    Process a reading logged event, creating a CollectionItemActivity of the appropriate status.
    """
    logger.info("Processing reading logged event")

    try:
        log_data = ReadingLogEvent.parse_obj(event.info.get("reading_logged"))
    except ValidationError as e:
        logger.warning("Error parsing reading logged event", error=e, event=event)
        return

    activity = CollectionItemActivityBase(
        collection_item_id=log_data.collection_item_id,
        reader_id=event.user_id,
        status=CollectionItemReadStatus.READ
        if log_data.finished
        else CollectionItemReadStatus.READING,
    )
    crud.collection_item_activity.create(session, obj_in=activity)


def update_or_create_liked_books(
    session: Session,
    liked_items: list[BookListItemUpdateIn],
    booklist_type: str,
    school: Optional[School],
    user: Optional[User],
    booklist_name="Liked Books",
):
    # See if the "Liked Books" booklist exists.
    liked_booklist_query = crud.booklist.get_all_query_with_optional_filters(
        db=session,
        list_type=booklist_type,
        school=school,
        user=user,
        query_string=booklist_name,
    )
    booklist = session.scalars(liked_booklist_query).first()
    if booklist is None:
        logger.info("Creating a new booklist", type=booklist_type)
        booklist = crud.booklist.create(
            db=session,
            obj_in=BookListCreateIn(
                name=booklist_name,
                type=booklist_type,
                user_id=user.id if user is not None else None,
                school_id=school.id if school is not None else None,
                info={"description": "List of all books liked in a Chat"},
                items=liked_items,
            ),
        )
    else:
        # Update with any newly liked items. Existing likes will be skipped
        logger.info("Updating existing booklist", booklist_id=booklist.id)
        booklist = crud.booklist.update(
            db=session, db_obj=booklist, obj_in=BookListUpdateIn(items=liked_items)
        )
    return booklist


def get_liked_books_from_book_review_event(session: Session, event: Event):
    liked_items = []
    logger.info("Getting liked books from event", event_info=event.info)

    if "reviews" not in event.info:
        logger.error("Unexpected event - couldn't find reviews")
        return []

    for review in event.info["reviews"]:
        logger.debug("Processing review", raw_review=review)
        edition = crud.edition.get(db=session, id=review["isbn"])
        if edition and review["liked"]:
            liked_items.append(
                BookListItemUpdateIn(
                    action=ItemUpdateType.ADD,
                    work_id=edition.work_id,
                    info=BookListItemInfo(
                        edition=review["isbn"],
                    ),
                )
            )
    return liked_items
