from urllib.parse import urlencode

from sqlalchemy.orm import Session
from structlog import get_logger

from app import crud
from app.models.collection_item import CollectionItem
from app.models.event import Event
from app.models.reader import Reader
from app.models.supporter import Supporter
from app.models.user import User
from app.schemas.events.event import EventCreateIn
from app.schemas.events.special_events import ReadingLogEvent
from app.schemas.feedback import SendSmsPayload
from app.schemas.sendgrid import SendGridEmailData
from app.services.background_tasks import queue_background_task
from app.services.util import truncate_to_full_word_with_ellipsis

logger = get_logger()


def generate_supporter_feedback_url(supporter: User, event: Event):
    # cannot wrestle with the circular imports, and this is a background process anyway
    from app.api.dependencies.security import create_user_access_token

    base_url = "https://huey-books--pr32-feature-supporter-fe-chu7p98q.web.app/reader-feedback/"
    data = {
        "event_id": str(event.id),
        "token": create_user_access_token(supporter),
    }
    encoded_url = f"{base_url}?{urlencode(data)}"

    return encoded_url


def process_supporter_feedback_submission(
    session: Session,
    reader: Reader,
    event: Event,
):
    pass


def process_reader_feedback_alert_email(
    recipient: Supporter,
    reader: Reader,
    item: CollectionItem,
    log_data: ReadingLogEvent,
    encoded_url: str,
):
    logger.info("Sending email alert")

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

    queue_background_task(
        "send-email", {"email_data": email_data.dict(), "user_id": str(reader.id)}
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
    for association in reader.supporter_associations:
        if association.is_active:
            recipient: User = association.supporter

            encoded_url = generate_supporter_feedback_url(recipient, event)
            sent = False

            if association.allow_email and recipient.email:
                process_reader_feedback_alert_email(
                    recipient, reader, item, log_data, encoded_url
                )
                sent = True

            if association.allow_phone and recipient.phone:
                process_reader_feedback_alert_sms(
                    recipient, reader, item, log_data, encoded_url
                )
                sent = True

            if not sent:
                logger.warning(
                    "Supporter has no active email or phone number to accept alerts",
                    supporter_id=recipient.id,
                    reader_id=reader.id,
                )
                return

            crud.event.create(
                session,
                EventCreateIn(
                    title="Alert Sent: Reading Logged",
                    description=f"Alert re: {reader.name}'s reading was sent to {recipient.type}: {recipient.email or recipient.phone}",
                    user_id=reader.id,
                    info={
                        "type": "Reading Log Feedback: Alert Sent",
                        "recipient": recipient,
                        "event_id": str(event.id),
                    },
                ),
            )
