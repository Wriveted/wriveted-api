import stripe as stripe

from fastapi import Request, Header
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
    logger.warning("Have stripe webhook secret", secret=endpoint_secret, stripe_header=stripe_signature)
    logger.warning("Body", body=payload)
    try:
        event = stripe.Webhook.construct_event(
            payload,
            stripe_signature,
            endpoint_secret)
    except ValueError as e:
        # Invalid payload
        raise e
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        raise e
    return event
