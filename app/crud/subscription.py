from typing import Tuple
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.crud import CRUDBase
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.subscription import SubscriptionCreateIn, SubscriptionUpdateIn


class CRUDSubscription(
    CRUDBase[Subscription, SubscriptionCreateIn, SubscriptionUpdateIn]
):
    def get_or_create(
        self,
        db: Session,
        subscription_data: SubscriptionCreateIn,
        commit: bool = True,
    ) -> Tuple[Subscription, bool]:
        q = select(Subscription).where(Subscription.id == subscription_data.id)
        subscription = db.execute(q).scalar_one_or_none()

        if subscription is None:
            subscription = Subscription(
                id=subscription_data.id,
                stripe_customer_id=subscription_data.stripe_customer_id,
                user_id=subscription_data.user_id,
            )
            db.add(subscription)

            if commit:
                db.commit()

            db.refresh(subscription)
            return subscription, True

        return subscription, False

    def get_by_stripe_customer_id(
        self, db: Session, *, stripe_customer_id: str
    ) -> Subscription:
        q = (
            select(User)
            .join(Subscription)
            .where(Subscription.stripe_customer_id == stripe_customer_id)
        )
        return db.execute(q).scalar_one_or_none()

    def get_by_checkout_session_id(
        self, db: Session, *, checkout_session_id: str
    ) -> Subscription | None:
        q = (
            select(User)
            .join(Subscription)
            .where(Subscription.latest_checkout_session_id == checkout_session_id)
        )
        return db.execute(q).scalar_one_or_none()


subscription = CRUDSubscription(Subscription)
