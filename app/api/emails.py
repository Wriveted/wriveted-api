from fastapi import APIRouter, BackgroundTasks, Depends, Response
from structlog import get_logger
from app.api.dependencies.security import (
    get_current_active_superuser_or_backend_service_account,
)
from app.config import get_settings
from sqlalchemy.orm import Session
from app.db.session import get_session
from app.schemas.email import EmailData
from app.services.emails import send_sendgrid_email

router = APIRouter(
    tags=["Emails"],
    dependencies=[Depends(get_current_active_superuser_or_backend_service_account)],
)

logger = get_logger()
config = get_settings()


@router.post("/email", include_in_schema=False)
async def send_email(
    data: EmailData,
    background_tasks: BackgroundTasks,
    account=Depends(get_current_active_superuser_or_backend_service_account),
    session: Session = Depends(get_session)
):
    """
    Populate and send a dynamic SendGrid email.
    Can dynamically fill a specified template with provided data.
    """
    logger.info("SendGrid email endpoint called", parameters=data, account=account)

    background_tasks.add_task(send_sendgrid_email, data, session, account)

    return Response(status_code=200, content="Email queued.")
