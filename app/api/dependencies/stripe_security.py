import stripe as stripe
from fastapi import Header, HTTPException, Request
from starlette import status
from structlog import get_logger

from app.config import get_settings

logger = get_logger()
config = get_settings()


async def get_stripe_event(
    request: Request,
    stripe_signature: str = Header(),
) -> stripe.Event:
    """A FastAPI dependency to get and verify the Stripe signature."""
    payload = await request.body()
    endpoint_secret = config.STRIPE_WEBHOOK_SECRET
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, endpoint_secret
        )
    except ValueError as e:
        logger.warning("Invalid payload", payload=payload, exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload"
        )
    except stripe.error.SignatureVerificationError as e:
        logger.warning("Invalid signature", payload=payload, exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature"
        )
    return event
