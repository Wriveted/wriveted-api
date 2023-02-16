from sqlalchemy.orm import Session
from structlog import get_logger
from app.api.dependencies.security import create_user_access_token
from app.models.collection_item import CollectionItem
from app.models.reader import Reader
from app.models.event import Event
from app.models.supporter import Supporter
from app.models.supporter_reader_association import SupporterReaderAssociation
from app.schemas.events.event import EventCreateIn
from app.schemas.events.special_events import ReadingLogEvent
from app.schemas.feedback import SendSmsPayload
from app.schemas.sendgrid import SendGridEmailData
from app.services.background_tasks import queue_background_task
from app import crud

from urllib.parse import urlencode

logger = get_logger()


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
    event: Event,
    log_data: ReadingLogEvent,
):
    logger.info("Sending email alert")
    email_data = SendGridEmailData(
        to_emails=[recipient.email],
        subject=f"{reader.name} has done some reading!",
        template_data={
            "nickname": recipient.name,
            "reader_name": reader.name,
            "book_title": item.get_display_title(),
            "event_id": str(event.id),
            "token": "The email should contain a magic link, so we need to include a token for the parent or reader",
            "emoji": log_data.emoji,
            "descriptor": log_data.descriptor,
        },
        template_id="xxx",
    )
    queue_background_task(
        "send-email", {"email_data": email_data, "user_id": str(reader.id)}
    )


def process_reader_feedback_alert_sms(
    recipient: Supporter,
    reader: Reader,
    item: CollectionItem,
    event: Event,
    log_data: ReadingLogEvent,
):
    logger.info("Sending sms alert")
    base_url = "https://hueybooks.com/reader-feedback/"
    data = {
        "event_id": str(event.id),
        "token": create_user_access_token(recipient),
    }
    url = f"{base_url}?{urlencode(data)}"

    sms_data = SendSmsPayload(
        to=recipient.phone,
        body=f"{reader.name} read some of {item.get_display_title()}, and described it as '{log_data.descriptor} {log_data.emoji}'.\nChoose a one-tap response: {url}\nHuey Books",
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
    active_supporters = (
        session.query(Supporter)
        .join(SupporterReaderAssociation)
        .filter(SupporterReaderAssociation.reader_id == reader.id)
        .filter(SupporterReaderAssociation.active == True)
        .all()
    )

    for recipient in active_supporters:
        if recipient.email:
            process_reader_feedback_alert_email(
                recipient, reader, item, event, log_data
            )

        elif recipient.phone:
            process_reader_feedback_alert_sms(recipient, reader, item, event, log_data)

        else:
            logger.warning(
                "Supporter has no email or phone number",
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
