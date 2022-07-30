from fastapi import APIRouter, BackgroundTasks, Body, Depends, Response, HTTPException
from pydantic import parse_obj_as
from structlog import get_logger
from app.api.dependencies.security import (
    get_current_active_superuser_or_backend_service_account,
)
from app.config import get_settings
from sqlalchemy.orm import Session
from app.db.session import get_session
from app.services.sendgrid import (
    get_sendgrid_custom_fields,
    send_sendgrid_email,
    upsert_sendgrid_contact,
)
from app.schemas.sendgrid import (
    SendGridCustomField,
    SendGridEmailData,
    SendGridContactData,
    CustomSendGridContactData
)

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
):
    """
    Upserts a SendGrid contact with provided data
    """
    logger.info(
        "SendGrid contact upsert endpoint called", parameters=data, account=account
    )

    if custom_fields:
        # enrich the 'named' custom fields with their equivalent sendgrid ids, provided they exist
        supplied_fields: list[SendGridCustomField] = parse_obj_as(
            list[SendGridCustomField], custom_fields
        )
        validated_fields: dict[str, int | str] = {}

        current_fields = get_sendgrid_custom_fields()
        for supplied_field in supplied_fields:
            id = next(
                (field.id for field in current_fields if field.name == supplied_field.name),
                None,
            )
            if id:
                validated_fields[id] = supplied_field.value
            else:
                raise HTTPException(
                    status_code=422,
                    detail=f"No custom field exists with the name {supplied_field.name}.",
                )

        payload = CustomSendGridContactData(**data.dict(), custom_fields=validated_fields)
        
    else:        
        payload = data

    # schedule the update
    background_tasks.add_task(upsert_sendgrid_contact, payload, session, account)

    return Response(status_code=202, content="Contact upsert queued.")


@router.post("/sendgrid/email", include_in_schema=False)
async def send_email(
    data: SendGridEmailData,
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
