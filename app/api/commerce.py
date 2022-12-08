import stripe
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    HTTPException,
    Query,
    Response,
)
from sendgrid import SendGridAPIClient
from sqlalchemy.orm import Session
from structlog import get_logger
from structlog.contextvars import bind_contextvars

from app.api.dependencies.security import (
    get_current_active_superuser_or_backend_service_account,
    verify_shopify_hmac,
)
from app.api.dependencies.stripe_security import get_stripe_event
from app.config import get_settings
from app.db.session import get_session
from app.schemas.sendgrid import (
    CustomSendGridContactData,
    SendGridContactData,
    SendGridCustomField,
    SendGridEmailData,
)
from app.schemas.shopify import ShopifyEventRoot
from app.services.background_tasks import queue_background_task
from app.services.commerce import (
    get_sendgrid_api,
    process_shopify_order,
    upsert_sendgrid_contact,
    validate_sendgrid_custom_fields,
)

router = APIRouter(tags=["Commerce"], include_in_schema=False)

logger = get_logger()
config = get_settings()


@router.put("/sendgrid/contact")
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


@router.post("/sendgrid/email")
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
    logger.info("Public email endpoint called", parameters=data, account=account)
    queue_background_task(
        "send-email", {"email_data": dict(data), "service_account_id": str(account.id)}
    )
    return Response(status_code=202, content="Email queued.")


@router.post(
    "/shopify/order-creation",
    dependencies=[Depends(verify_shopify_hmac)],
)
async def create_shopify_order(
    data: ShopifyEventRoot,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    sg: SendGridAPIClient = Depends(get_sendgrid_api),
):
    """
    Endpoint for the Webhook called by Shopify when a customer places an order.
    Upserts equivalent SendGrid contact with basic info about the order, and logs an event with the details.
    """
    background_tasks.add_task(process_shopify_order, data, sg, session)

    return Response(status_code=200, content="Thanks Shopify")


@router.post(
    "/stripe/webhook",
)
async def process_stripe_webhook(
    event: stripe.Event = Depends(get_stripe_event),
    session: Session = Depends(get_session),
):
    """
    Endpoint for the Webhook called by Stripe.

    https://stripe.com/docs/webhooks
    """

    logger.info("Received an event from Stripe", stripe_event_type=event.type)
    event_data = event.data["object"]
    bind_contextvars(stripe_event_type=event.type)

    if "customer" in event_data:
        bind_contextvars(stripe_customer_id=event_data["customer"])

    match event.type:
        # Customer events
        case "customer.created":
            logger.info("Stripe customer created")
            logger.info("Payload", stripe_event_data=event_data)
        case "customer.updated":
            logger.info("Stripe customer updated")
        # Subscription events
        case "customer.subscription.created":
            logger.info("Subscription created")
            logger.info("Payload", stripe_event_data=event_data)
            logger.info("Scheduling task to update User with Stripe customer")

            # TODO: Work out how to link User and Stripe customer
            # Schedule a background task to update the User with the Stripe customer ID

        case "customer.subscription.updated":
            logger.info("Subscription created")
        case "customer.subscription.deleted":
            logger.info("Subscription deleted")

        # Payment events
        case "payment_intent.succeeded":
            logger.info("Payment intent succeeded")
        case "payment_intent.payment_failed":
            logger.warning("Payment failed")

        case _:
            logger.info("Unhandled Stripe event", stripe_event_type=event.type)
            logger.debug("Stripe event data", stripe_event_data=event.data)

    return {"status": "success"}
