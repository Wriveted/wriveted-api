from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, BaseSettings
from sendgrid import SendGridAPIClient
from sqlalchemy.orm import Session
from structlog import get_logger

from app import crud
from app.db.session import get_session
from app.models.event import EventSlackChannel
from app.schemas.feedback import SendEmailPayload, SendSmsPayload
from app.schemas.sendgrid import SendGridEmailData
from app.schemas.users.huey_attributes import HueyAttributes
from app.services.booklists import generate_reading_pathway_lists
from app.services.commerce import (
    get_sendgrid_api,
    get_twilio_client,
    send_sendgrid_email,
)
from app.services.events import handle_event_to_slack_alert, process_events
from app.services.stripe_events import process_stripe_event
from twilio.rest import Client as TwilioClient


class CloudRunEnvironment(BaseSettings):
    K_SERVICE: str = None
    K_REVISION: str = None
    K_CONFIGURATION: str = None


cloud_run_config = CloudRunEnvironment()

logger = get_logger()

router = APIRouter()


@router.get("/version")
async def get_version():
    cloud_run_revision = cloud_run_config.K_REVISION or "Unknown"
    return {"cloud_run_revision": cloud_run_revision, "version": "internal"}


class ProcessEventPayload(BaseModel):
    event_id: str


@router.post("/process-event")
async def process_event(data: ProcessEventPayload):
    return process_events(
        event_id=data.event_id,
    )


class EventSlackAlertPayload(BaseModel):
    event_id: str
    slack_channel: EventSlackChannel = EventSlackChannel.GENERAL
    slack_extra: dict[str, str] | None


@router.post("/event-to-slack-alert")
async def event_to_slack_alert(
    data: EventSlackAlertPayload,
    session: Session = Depends(get_session),
):
    logger.info("Internal API preparing to send event to slack", data=data)
    return handle_event_to_slack_alert(
        session, data.event_id, data.slack_channel, extra=data.slack_extra
    )


class StripeInternalEventPayload(BaseModel):
    stripe_event_type: str
    stripe_event_data: Any


@router.post("/process-stripe-event")
async def handle_stripe_event(data: StripeInternalEventPayload):
    logger.info("Internal API processing a stripe event", data=data)

    return process_stripe_event(
        event_type=data.stripe_event_type,
        event_data=data.stripe_event_data,
    )


class GenerateReadingPathwaysPayload(BaseModel):
    user_id: str
    attributes: HueyAttributes
    limit: int = 10


@router.post("/generate-reading-pathways")
def handle_generate_reading_pathways(data: GenerateReadingPathwaysPayload):
    logger.info(
        "Internal API starting generating reading pathways", user_id=data.user_id
    )
    generate_reading_pathway_lists(
        user_id=data.user_id,
        attributes=data.attributes,
        limit=data.limit,
        commit=False,  # NOTE commit disabled for testing
    )

    logger.info("Finished generating reading pathways", user_id=data.user_id)

    return {"msg": "ok"}


@router.post("/send-email")
def handle_send_email(
    data: SendEmailPayload,
    session: Session = Depends(get_session),
    sg: SendGridAPIClient = Depends(get_sendgrid_api),
):
    logger.info("Internal API sending emails")
    user_account = crud.user.get(db=session, id=data.user_id)
    svc_account = crud.service_account.get(db=session, id=data.service_account_id)
    account = user_account or svc_account
    send_sendgrid_email(data.email_data, session, sg, account=account)


@router.post("/send-sms")
def handle_send_sms(
    data: SendSmsPayload,
    client: TwilioClient = Depends(get_twilio_client),
):
    logger.info("Internal API sending sms", data=data)
    return client.messages.create(**data)
