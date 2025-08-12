from urllib.parse import urlencode

from sqlalchemy.orm import Session
from structlog import get_logger

from app import crud
from app.config import get_settings
from app.models.collection_item import CollectionItem
from app.models.event import Event, EventLevel
from app.models.reader import Reader
from app.models.supporter import Supporter
from app.models.user import User
from app.schemas.events.special_events import ReadingLogEvent
from app.schemas.feedback import SendSmsPayload
from app.schemas.sendgrid import SendGridEmailData
# Import needed for SMS notifications  
from app.services.background_tasks import queue_background_task
from app.services.util import truncate_to_full_word_with_ellipsis

logger = get_logger()
settings = get_settings()


def generate_supporter_feedback_url(supporter: User, event: Event):
    # cannot wrestle with the circular imports, and this is a background process anyway
    from app.api.dependencies.security import create_user_access_token

    base_url = f"{settings.HUEY_BOOKS_APP_URL}/reader-feedback/"
    data = {
        "event_id": str(event.id),
        "token": create_user_access_token(supporter),
    }
    encoded_url = f"{base_url}?{urlencode(data)}"

    return encoded_url


def process_reader_feedback_alert_email(
    session,
    recipient: Supporter,
    reader: Reader,
    item: CollectionItem,
    log_data: ReadingLogEvent,
    encoded_url: str,
):
    logger.info("Sending reading feedback email")

    email_data = SendGridEmailData(
        to_emails=[recipient.email],
        subject=f"{reader.name} has done some reading!",
        from_name="Huey Books",
        template_data={
            "supporter_name": recipient.name,
            "reader_name": reader.name,
            "book_title": item.get_display_title(),
            "emoji": log_data.emoji,
            "descriptor": log_data.descriptor,
            "encoded_url": encoded_url,
        },
        template_id="d-841938d74d9142509af934005ad6e3ed",
    )

    # Local import to avoid circular dependency
    from app.services.email_notification import send_email_reliable_sync, EmailType
    
    send_email_reliable_sync(
        db=session,
        email_data=email_data.dict(),
        email_type=EmailType.NOTIFICATION,
        user_id=str(reader.id)
    )


def process_reader_feedback_alert_sms(
    recipient: Supporter,
    reader: Reader,
    item: CollectionItem,
    log_data: ReadingLogEvent,
    encoded_url: str,
):
    logger.info("Sending sms alert")

    template_data = {
        "name": reader.name,
        "title": truncate_to_full_word_with_ellipsis(item.get_display_title(), 30),
        "descriptor": log_data.descriptor,
        "emoji": log_data.emoji,
        "url": encoded_url,
    }

    template = "{name} read some of {title}, and described it as '{descriptor} {emoji}'.\nChoose a one-tap response: {url}\nHuey Books"

    sms_data = SendSmsPayload(
        to=recipient.phone,
        body=template.format(**template_data),
        shorten_urls=True,
    )

    queue_background_task(
        "send-sms",
        sms_data,
    )


def process_reader_feedback_alerts(
    session: Session,
    reader: Reader,
    item: CollectionItem,
    event: Event,
    log_data: ReadingLogEvent,
):
    active_associations = [
        association
        for association in reader.supporter_associations
        if association.is_active and association.allow_email or association.allow_phone
    ]
    logger.info(
        f"About to alert {len(active_associations)} Supporters",
        reader=reader,
    )
    for association in active_associations:
        recipient: User = association.supporter

        encoded_url = generate_supporter_feedback_url(recipient, event)

        if association.allow_email and recipient.email:
            process_reader_feedback_alert_email(
                session, recipient, reader, item, log_data, encoded_url
            )

        if association.allow_phone and recipient.phone:
            process_reader_feedback_alert_sms(
                recipient, reader, item, log_data, encoded_url
            )

        crud.event.create(
            session,
            title="Notification Sent: Reading Logged",
            level=EventLevel.DEBUG,
            description=f"Notification re: {reader.name}'s reading was sent to {recipient.type}: {recipient.email or recipient.phone}",
            account=reader,
            info={
                "recipient_id": str(recipient.id),
                "recipient_type": recipient.type,
                "event_id": str(event.id),
            },
        )
