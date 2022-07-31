from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    Query,
    Response,
    HTTPException,
)
from structlog import get_logger
from app.api.dependencies.security import (
    get_current_active_superuser_or_backend_service_account,
)
from app.config import get_settings
from sqlalchemy.orm import Session
from app.db.session import get_session
from app.services.sendgrid import (
    get_sendgrid_api,
    send_sendgrid_email,
    upsert_sendgrid_contact,
    validate_sendgrid_custom_fields,
)
from app.schemas.sendgrid import (
    SendGridCustomField,
    SendGridEmailData,
    SendGridContactData,
    CustomSendGridContactData,
)
from sendgrid import SendGridAPIClient

router = APIRouter(
    tags=["SendGrid"],
    dependencies=[Depends(get_current_active_superuser_or_backend_service_account)],
)

logger = get_logger()
config = get_settings()


@router.put("/sendgrid/contact", include_in_schema=False)
async def upsert_contact(
    data: SendGridContactData,
    background_tasks: BackgroundTasks,
    custom_fields: list[SendGridCustomField] = Body(default=None),
    account=Depends(get_current_active_superuser_or_backend_service_account),
    session: Session = Depends(get_session),
    increment_children: bool | None = Query(False),
    sg: SendGridAPIClient = Depends(get_sendgrid_api),
):
    """
    Upserts a SendGrid contact with provided data
    """
    logger.info(
        "SendGrid contact upsert endpoint called", parameters=data, account=account
    )

    if custom_fields:
        try:
            validated_fields = validate_sendgrid_custom_fields(custom_fields, sg)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

        payload = CustomSendGridContactData(
            **data.dict(), custom_fields=validated_fields
        )

    else:
        payload = data

    # schedule the update
    background_tasks.add_task(
        upsert_sendgrid_contact, payload, session, account, sg, increment_children
    )

    return Response(status_code=202, content="Contact upsert queued.")


@router.post("/sendgrid/email", include_in_schema=False)
async def send_email(
    data: SendGridEmailData,
    background_tasks: BackgroundTasks,
    account=Depends(get_current_active_superuser_or_backend_service_account),
    session: Session = Depends(get_session),
    sg: SendGridAPIClient = Depends(get_sendgrid_api),
):
    """
    Populate and send a dynamic SendGrid email.
    Can dynamically fill a specified template with provided data.
    """
    logger.info("SendGrid email endpoint called", parameters=data, account=account)
    background_tasks.add_task(send_sendgrid_email, data, session, account, sg)

    return Response(status_code=202, content="Email queued.")
