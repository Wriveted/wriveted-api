from fastapi import APIRouter, Depends
from pydantic import BaseModel, BaseSettings
from sendgrid import SendGridAPIClient
from sqlalchemy.orm import Session
from structlog import get_logger

from app import crud
from app.db.session import get_session
from app.schemas.sendgrid import SendGridEmailData
from app.schemas.users.huey_attributes import HueyAttributes
from app.services.booklists import generate_reading_pathway_lists
from app.services.commerce import get_sendgrid_api, send_sendgrid_email
from app.services.events import process_events


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


class SendEmailPayload(BaseModel):
    email_data: SendGridEmailData
    user_id: str | None
    service_account_id: str | None


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
