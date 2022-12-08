from fastapi import Depends, Header


def get_stripe_event(
    payload: Any,
    stripe_signature: Header = Depends(Header("STRIPE_SIGNATURE")),
) -> str:
    """A FastAPI dependency to get and verify the Stripe signature."""
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError as e:
        # Invalid payload
        raise e
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        raise e
    return event
