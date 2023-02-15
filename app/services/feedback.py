from sqlalchemy.orm import Session
from structlog import get_logger
from app.api.internal import SendSmsPayload
from app.models.collection_item import CollectionItem
from app.models.reader import Reader
from app.models.event import Event
from app.schemas.events.event import EventCreateIn
from app.schemas.events.special_events import ReadingLogEvent
from app.schemas.sendgrid import SendGridEmailData
from app.schemas.users.huey_attributes import AlertRecipient
from app.services.background_tasks import queue_background_task
from app import crud

logger = get_logger()


def process_reader_feedback_alerts(
    session: Session,
    reader: Reader,
    item: CollectionItem,
    event: Event,
    log_data: ReadingLogEvent,
    recipients: list[AlertRecipient],
):
    for recipient in recipients:
        if recipient.type == "email":
            logger.info("Sending email alert")
            email_data = SendGridEmailData(
                to_emails=[recipient.email],
                subject=f"{reader.name} has done some reading!",
                template_data={
                    "nickname": recipient.nickname,
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

        elif recipient.type == "phone":
            logger.info("Sending sms alert")
            magic_feedback_code = {
                "event_id": str(event.id),
                "token": "Some kind of jwt token? Encoded with the secret, containing the event id and recipient's phone number / email?",
            }
            sms_data = SendSmsPayload(
                to=recipient.phone,
                body=f"{reader.name} read some of {item.get_display_title()}, and described it as '{log_data.descriptor} {log_data.emoji}'.\nChoose a one-tap response: https://hueybooks.com/reader-feedback/{magic_feedback_code}\nReply STOP to unsub.",
                shorten_urls=True,
            )

            queue_background_task(
                "send-sms",
                sms_data,
            )

        crud.event.create(
            session,
            EventCreateIn(
                title="Alert Sent: Reading Logged",
                description=f"Alert re: {reader.name}'s reading was sent to {recipient.type} {recipient.email or recipient.phone}",
                user_id=reader.id,
                info={
                    "type": "Reading Log Feedback: Alert Sent",
                    "recipient": recipient,
                    "event_id": str(event.id),
                },
            ),
        )
