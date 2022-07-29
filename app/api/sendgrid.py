from fastapi import APIRouter, BackgroundTasks, Depends, Response
from structlog import get_logger
from app.api.dependencies.security import (
    get_current_active_superuser_or_backend_service_account,
)
from app.config import get_settings
from sqlalchemy.orm import Session
from app.db.session import get_session
from app.schemas.sendgrid import ContactData, EmailData
from app.services.sendgrid import send_sendgrid_email, upsert_sendgrid_contact

router = APIRouter(
    tags=["SendGrid"],
    dependencies=[Depends(get_current_active_superuser_or_backend_service_account)],
)

logger = get_logger()
config = get_settings()


@router.put("/sendgrid/contact", include_in_schema=False)
async def upsert_contact(
    data: ContactData,
    background_tasks: BackgroundTasks,
    account=Depends(get_current_active_superuser_or_backend_service_account),
    session: Session = Depends(get_session),
):
    """
    Upserts a SendGrid contact with provided data
    """
    logger.info(
        "SendGrid contact upsert endpoint called", parameters=data, account=account
    )
    background_tasks.add_task(upsert_sendgrid_contact, data, session, account)

    return Response(status_code=202, content="Contact upsert queued.")


@router.post("/sendgrid/email", include_in_schema=False)
async def send_email(
    data: EmailData,
    background_tasks: BackgroundTasks,
    account=Depends(get_current_active_superuser_or_backend_service_account),
    session: Session = Depends(get_session),
):
    """
    Populate and send a dynamic SendGrid email.
    Can dynamically fill a specified template with provided data.
    """
    logger.info("SendGrid email endpoint called", parameters=data, account=account)
    background_tasks.add_task(send_sendgrid_email, data, session, account)

    return Response(status_code=202, content="Email queued.")
