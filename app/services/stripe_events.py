from typing import Optional, Tuple

import stripe
from stripe.api_resources.customer import Customer
from structlog import get_logger
from structlog.contextvars import bind_contextvars

from app import crud
from app.db.session import get_session_maker
from app.models import User

logger = get_logger()


def process_stripe_event(event_type: str, event_data):
    logger.info(
        "Processing a stripe event", event_type=event_type, event_data=event_data
    )
    bind_contextvars(stripe_event_type=event_type)

    Session = get_session_maker()
    with Session() as session:
        if "customer" in event_data:
            customer_id = event_data["customer"]
            wriveted_user, customer_detail = get_user_for_stripe_customer(
                session, customer_id
            )
            bind_contextvars(stripe_customer_id=customer_id, user=wriveted_user)
        else:
            wriveted_user = None

        match event_type:
            # Customer events
            case "customer.created":
                logger.info("Stripe customer created")
                logger.info("Payload", stripe_event_data=event_data)
                if wriveted_user:
                    logger.info("Updating user info with stripe customer id")
                    wriveted_user.info["stripe_customer_id"] = event_data["customer"]
                else:
                    logger.warning("No user found for Stripe customer")

            case "customer.updated":
                logger.info("Stripe customer updated. Not taking any action")

            # Subscription events
            case "customer.subscription.created":
                logger.info("Processing a subscription created event")
                logger.info("Payload", stripe_event_data=event_data)

                if wriveted_user is None:
                    logger.warning("No Wriveted user found for this email!")

                    # TODO: Send an email to the customer to let them know
                    # that we couldn't find their account, and with instructions
                    # to link their subscription to their existing Wriveted account
                else:
                    logger.info("Updating Wriveted user")
                    wriveted_user.is_active = True
                    wriveted_user.info["stripe_subscription_id"] = event_data["id"]
                    logger.info("Finished processing a subscription created event")
            case "customer.subscription.updated":
                logger.info("Subscription updated. Not taking an action")
            case "customer.subscription.deleted":
                if wriveted_user is None:
                    logger.warning("No Wriveted user found for this email!")
                else:
                    logger.info("Subscription deleted. Marking user as inactive")
                    wriveted_user.is_active = False

            # Checkout session events
            case "checkout.session.completed":
                crud.event.create(
                    session=session, title="Checkout session completed", info=event_data
                )
                # This event is triggered when a checkout session is completed successfully.
                # It contains the custom field `client_reference_id` which we use to look up
                # the Wriveted user and link the Stripe customer to the Wriveted user.
                customer_wriveted_id = event_data.get("client_reference_id")
                if customer_wriveted_id is not None:
                    logger.info(
                        "Checkout session completed for a Wriveted user",
                        customer_wriveted_id=customer_wriveted_id,
                    )
                else:
                    logger.info("Checkout session completed for a non-Wriveted user")

                logger.info("Checkout session completed")
                logger.info("Payload", stripe_event_data=event_data)

            # Payment events
            case "payment_intent.succeeded":
                logger.info("Payment succeeded")
            case "payment_intent.payment_failed":
                logger.warning("Payment failed")

            case _:
                logger.info("Unhandled Stripe event")
                logger.debug("Stripe event data", stripe_event_data=event_data)


def get_user_for_stripe_customer(
    session, customer_id
) -> Tuple[Optional[User], Customer]:
    # This will be refactored to first look up the database for a Wriveted User by the
    # Stripe Customer ID, with a fallback to asking Stripe for the Customer's email.
    # Note the customer detail won't have an email address after they are deleted on the
    # Stripe side.
    logger.info("Looking up stripe customer details")
    customer_detail = stripe.Customer.retrieve(customer_id)
    logger.info("Customer detail", customer_detail=customer_detail)
    customer_email = customer_detail.get("email")
    if customer_email is not None:
        logger.info("Customer email", customer_email=customer_email)
        wriveted_user = crud.user.get_by_account_email(db=session, email=customer_email)
    else:
        logger.warning("No email found for customer")
        wriveted_user = None

    return wriveted_user, customer_detail
