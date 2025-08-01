from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud import CRUDBase
from app.models.subscription import Subscription
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
            subscription = self.create(db, obj_in=subscription_data, commit=commit)
            db.refresh(subscription)
            return subscription, True

        return subscription, False

    def get_by_stripe_customer_id(
        self, db: Session, *, stripe_customer_id: str
    ) -> Optional[Subscription]:
        q = select(Subscription).where(Subscription.stripe_customer_id == stripe_customer_id)
        return db.execute(q).scalar_one_or_none()

    def get_by_checkout_session_id(
        self, db: Session, *, checkout_session_id: str
    ) -> Subscription | None:
        q = select(Subscription).where(
            Subscription.latest_checkout_session_id == checkout_session_id
        )
        return db.execute(q).scalar_one_or_none()

    def upsert(
        self,
        db: Session,
        subscription_data: SubscriptionCreateIn,
        commit: bool = True,
    ) -> Subscription:
        sub, created = self.get_or_create(
            db=db, subscription_data=subscription_data, commit=commit
        )
        if not created:
            sub = self.update(
                db=db, db_obj=sub, obj_in=subscription_data, commit=commit
            )
        return sub


subscription = CRUDSubscription(Subscription)
