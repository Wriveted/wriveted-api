from stripe import (
    Subscription as StripeSubscription,
    Customer as StripeCustomer,
    Price as StripePrice,
    Product as StripeProduct,
)
from structlog import get_logger
from structlog.contextvars import bind_contextvars

from app import crud
from app.db.session import get_session_maker
from app.models import User
from app.models.product import Product
from app.models.subscription import Subscription
from app.models.user import UserAccountType
from app.schemas.product import ProductCreateIn
from app.schemas.subscription import SubscriptionCreateIn, SubscriptionUpdateIn

logger = get_logger()


def process_stripe_event(event_type: str, event_data):
    """
    Processes an event sent by Stripe webhook.

    These webhook events are sent asynchronously, and order is not guaranteed -
    i.e. when a new customer subscribes, a `customer.subscription.created` event
    may be sent before a `customer.created` event.
    See https://stripe.com/docs/webhooks/best-practices#event-ordering

    Because of this, it may be wise to consider overarching transactions and use-cases,
    fetching data from Stripe as needed, rather than blindly processing each event separately.
    For example, when a new customer subscribes, we may want to establish a
    user/subscription/product relationship in a single transaction, rather than piecemeal.

    The main use-cases we want to handle at this stage are:
    - A brand new customer subscribes, without an existing account
    - An existing Free tier customer subscribes
    - An existing customer modifies their subscription (e.g. upgrades, downgrades, or cancels)

    We can still capture other events for logging purposes,
    but we need not apply any business logic in them.

    It's worth noting that it's only the events we receive that are asynchronous,
    not the underlying processes and database transactions at Stripe's end.
    So, for example, when a new customer successfully subscribes, and the following events are received
    in the order listed (with the actual chronological order of the underlying process in parentheses):

    (2) - `customer.subscription.created`
            (contains the `customer` id, information about the subscription)
    (3) - `checkout.session.completed`
            (contains the `customer` id, the `subscription` id, and any included
            `client_reference_id` sent by our frontend to identify the user)
    (1) - `customer.created`
            (contains the `customer` information, but no `subscription` information)

    We -could- handle each of these events separately (with the incomplete pictures they each provide),
    but will be able to handle them more efficiently if we target the event with the most significance and pointers/id's.

    For this example, it's most convenient to do this by only heavily processing the `checkout.session.completed`
    event, which includes id's for relevant instances of `customer` and `subscription` (and by extension `price`/`product`) in its payload.
    As this is the chronologically final event in this use-case, we can then simply query the Stripe API for the
    relevant instances of `customer` and `subscription`, knowing that Stripe has already processed these.
    This effectively gives us the full picture in a single event, instead of waiting for and blindly processing the
    `customer.created` and `customer.subscription.created` events.
    """

    object_type = event_data.get("object")

    logger.info(
        "Processing a stripe event", event_type=event_type, event_data=event_data
    )
    bind_contextvars(stripe_event_type=event_type)

    Session = get_session_maker()
    with Session() as session:
        wriveted_user = None

        # webhook is only listening to events that are guaranteed to include a customer id (for now)
        stripe_customer_id = (
            event_data.get("id")
            if object_type == "customer"
            else event_data.get("customer")
        )
        if stripe_customer_id:
            stripe_customer = StripeCustomer.retrieve(stripe_customer_id)
            bind_contextvars(stripe_customer_id=stripe_customer_id)

        # check customer metadata for a wriveted user id
        # (this is stored upon the first successful checkout)
        if user_id := stripe_customer.metadata.get("wriveted_id"):
            wriveted_user = crud.user.get(session, user_id)
            logger.info(
                "Found wriveted user id in customer metadata", user=wriveted_user
            )
            bind_contextvars(wriveted_user_id=str(wriveted_user.id))

        # check for any custom client_reference_id injected by our frontend (a Wriveted user id)
        # note: empty values can sometimes be returned as the strings "undefined" or "null"
        client_reference_id = event_data.get("client_reference_id")
        if client_reference_id == "undefined" or client_reference_id == "null":
            client_reference_id = None

        if client_reference_id:
            if referenced_user := crud.user.get(session, client_reference_id):
                if wriveted_user and referenced_user != wriveted_user:
                    logger.warning(
                        "Client reference id does not match User associated with Stripe customer id",
                        referenced_user_id=referenced_user.id,
                    )
                    # TODO: Handle this case?
                else:
                    wriveted_user = referenced_user
                    logger.info(
                        "Client reference id matches User associated with Stripe customer id",
                        referenced_user_id=referenced_user.id,
                    )
            else:
                logger.warning(
                    "Client reference id does not match any user",
                    client_reference_id=client_reference_id,
                )
                # TODO: Handle this case?

        if wriveted_user:
            bind_contextvars(wriveted_user_id=str(wriveted_user.id))

        # we now have a stripe customer and, if it exists, equivalent wriveted user

        match event_type:
            # Actionable events
            case "checkout.session.completed":  # https://stripe.com/docs/api/checkout/sessions/object
                logger.info("Checkout session completed. Creating subscription")
                _handle_checkout_session_completed(session, wriveted_user, event_data)

            case "customer.subscription.updated":  # https://stripe.com/docs/api/subscriptions/object
                logger.info(
                    "Subscription updated. Updating underlying product or plan if necessary"
                )
                _handle_subscription_updated(session, wriveted_user, event_data)

            case "customer.subscription.deleted":  # https://stripe.com/docs/api/subscriptions/object
                logger.info("Subscription deleted. Removing subscription from user")
                _handle_subscription_cancelled(session, wriveted_user, event_data)

            # Log-and-move-on events
            case "customer.created":
                logger.info("Stripe customer created")

            case "customer.updated":
                logger.info("Stripe customer updated. Not taking any action")

            case "customer.subscription.created":
                logger.info(
                    "Stripe subscription created",
                    stripe_subscription_id=event_data.get("subscription"),
                )

            case "payment_intent.succeeded":
                logger.info("Payment succeeded")

            case "payment_intent.payment_failed":
                logger.warning("Payment failed")

            case _:
                logger.info("Unhandled Stripe event")
                logger.debug("Stripe event data", stripe_event_data=event_data)


def _handle_checkout_session_completed(
    session, wriveted_user: User, event_data: dict
) -> Subscription:
    # in this case we want to query the Stripe API for the subscription and customer,
    # as we know they exist and have been processed by Stripe.
    # we can then use this information to create a new subscription in our database (if needed),
    # and link the customer to the user (if needed).
    stripe_subscription_id = event_data.get("subscription")
    stripe_subscription = StripeSubscription.retrieve(stripe_subscription_id)

    stripe_customer_id = stripe_subscription.customer
    stripe_customer = StripeCustomer.retrieve(stripe_customer_id)

    if wriveted_user and not stripe_customer.metadata.get("wriveted_id"):
        # we have a wriveted user, but no wriveted id on the stripe customer
        logger.info(
            "Updating Stripe customer metadata with Wriveted user id",
            stripe_customer_id=stripe_customer_id,
        )
        stripe_customer.metadata["wriveted_id"] = str(wriveted_user.id)
        stripe_customer.save()

    # ensure our db knows about the specified product
    stripe_price_id = stripe_subscription["items"]["data"][0]["price"]["id"]
    logger.info(
        "Ensuring product %s exists in our database",
        stripe_subscription=stripe_subscription,
    )
    _sync_stripe_price_with_wriveted_product(session, stripe_price_id)

    # create or update a base subscription in our database
    base_subscription_data = SubscriptionCreateIn(
        id=stripe_subscription_id,
        product_id=stripe_price_id,
        stripe_customer_id=stripe_subscription.customer,
        parent_id=str(wriveted_user.id)
        if wriveted_user and wriveted_user.type == UserAccountType.PARENT
        else None,
    )
    logger.info(
        "Creating or updating subscription in our database",
        base_subscription_data=base_subscription_data,
    )
    subscription = crud.subscription.get_or_create(session, base_subscription_data)[0]

    # populate the subscription in our database with the latest information
    current_subscription_data = SubscriptionUpdateIn(
        is_active=True,
        # we store the checkout session id in the subscription so that we can
        # retrieve it later (in the case that a user hasn't yet signed up nor logged in,
        # and need to link this subscription to their account once they have).
        latest_checkout_session_id=event_data.get("id"),
    ).dict(exclude_unset=True)

    subscription = crud.subscription.update(
        session, db_obj=subscription, obj_in=current_subscription_data
    )

    crud.event.create(
        session=session,
        title="Checkout session completed",
        description="Subscription created or updated for stripe customer",
        info={
            "stripe_customer_id": stripe_customer_id,
            "stripe_subscription_id": stripe_subscription_id,
        },
        account=wriveted_user,
    )

    return subscription


def _handle_subscription_updated(
    session, wriveted_user: User, event_data: dict
) -> Subscription:
    stripe_subscription_id = event_data.get("id")
    stripe_subscription = StripeSubscription.retrieve(stripe_subscription_id)
    stripe_subscription_status = stripe_subscription.status

    # ensure our db knows about the specified product
    stripe_price_id = stripe_subscription["items"]["data"][0]["price"]["id"]
    _sync_stripe_price_with_wriveted_product(session, stripe_price_id)

    subscription = crud.subscription.get(session, id=stripe_subscription_id)
    if not subscription:
        return

    # populate the subscription in our database with the latest information
    current_subscription_data = SubscriptionUpdateIn(
        product_id=stripe_price_id,
        is_active=stripe_subscription_status == "active",
        latest_checkout_session_id=event_data.get("id"),
    ).dict()

    if wriveted_user and not subscription.parent_id:
        # we have a wriveted user, but no wriveted id on the subscription
        logger.info(
            "Updating subscription %s with Wriveted user id %s",
            stripe_subscription_id,
            wriveted_user.id,
        )
        current_subscription_data["wriveted_user_id"] = wriveted_user.id

    subscription = crud.subscription.update(
        session, db_obj=subscription, obj_in=current_subscription_data
    )
    crud.event.create(
        session=session,
        title="Stripe Subscription updated",
        description=f"User {wriveted_user.id} updated their subscription to {stripe_price_id}",
        info={
            "stripe_subscription_id": stripe_subscription_id,
            "product_id": stripe_price_id,
        },
        account=wriveted_user,
    )

    return subscription


def _handle_subscription_cancelled(session, wriveted_user: User, event_data: dict):
    stripe_subscription_id = event_data.get("id")
    subscription = crud.subscription.get(session, id=stripe_subscription_id)
    parent = subscription.parent
    product = subscription.product
    crud.subscription.remove(session, id=stripe_subscription_id)

    crud.event.create(
        session=session,
        title="Stripe Subscription cancelled",
        description=f"User {parent.id} cancelled their subscription to {product.name}",
        info={
            "stripe_subscription_id": stripe_subscription_id,
            "product_id": product.id,
        },
        account=wriveted_user,
    )


def _sync_stripe_price_with_wriveted_product(session, stripe_price_id: str) -> Product:
    logger.info("Syncing Stripe price %s with Wriveted product", stripe_price_id)
    wriveted_product = crud.product.get(session, id=stripe_price_id)
    if not wriveted_product:
        logger.info("Creating new product in db")
        stripe_price = StripePrice.retrieve(stripe_price_id)
        stripe_product = StripeProduct.retrieve(stripe_price.product)
        wriveted_product = crud.product.create(
            session,
            obj_in=ProductCreateIn(id=stripe_price_id, name=stripe_product.name),
        )
    else:
        logger.info("Product already exists in db")
    return wriveted_product
