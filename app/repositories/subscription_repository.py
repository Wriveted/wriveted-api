"""
Subscription Repository - Domain-focused data access for subscriptions.

Migrated from app.crud.subscription to follow repository pattern.
"""

from abc import ABC, abstractmethod
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.subscription import Subscription
from app.schemas.subscription import SubscriptionCreateIn, SubscriptionUpdateIn


class SubscriptionRepository(ABC):
    """Repository interface for Subscription operations."""

    @abstractmethod
    def get_by_id(self, db: Session, subscription_id: str) -> Optional[Subscription]:
        """Get subscription by ID."""
        pass

    @abstractmethod
    def get_or_create(
        self,
        db: Session,
        subscription_data: SubscriptionCreateIn,
        commit: bool = True,
    ) -> Tuple[Subscription, bool]:
        """
        Get or create a subscription.

        Returns:
            Tuple of (subscription, created) where created is True if newly created
        """
        pass

    @abstractmethod
    def get_by_stripe_customer_id(
        self, db: Session, stripe_customer_id: str
    ) -> Optional[Subscription]:
        """Get subscription by Stripe customer ID."""
        pass

    @abstractmethod
    def get_by_checkout_session_id(
        self, db: Session, checkout_session_id: str
    ) -> Optional[Subscription]:
        """Get subscription by checkout session ID."""
        pass

    @abstractmethod
    def upsert(
        self,
        db: Session,
        subscription_data: SubscriptionCreateIn,
        commit: bool = True,
    ) -> Subscription:
        """Upsert a subscription (create if not exists, update if exists)."""
        pass

    @abstractmethod
    def create(
        self,
        db: Session,
        obj_in: SubscriptionCreateIn,
        commit: bool = True,
    ) -> Subscription:
        """Create new subscription."""
        pass

    @abstractmethod
    def update(
        self,
        db: Session,
        db_obj: Subscription,
        obj_in: SubscriptionUpdateIn,
        commit: bool = True,
    ) -> Subscription:
        """Update existing subscription."""
        pass

    @abstractmethod
    def delete(self, db: Session, subscription_id: str, commit: bool = True) -> None:
        """Delete a subscription by ID."""
        pass


class SubscriptionRepositoryImpl(SubscriptionRepository):
    """SQLAlchemy implementation of SubscriptionRepository."""

    def get_by_id(self, db: Session, subscription_id: str) -> Optional[Subscription]:
        """Get subscription by ID."""
        return db.get(Subscription, subscription_id)

    def get_or_create(
        self,
        db: Session,
        subscription_data: SubscriptionCreateIn,
        commit: bool = True,
    ) -> Tuple[Subscription, bool]:
        """
        Get or create a subscription.

        Returns:
            Tuple of (subscription, created) where created is True if newly created
        """
        q = select(Subscription).where(Subscription.id == subscription_data.id)
        subscription = db.execute(q).scalar_one_or_none()

        if subscription is None:
            subscription = self.create(db, obj_in=subscription_data, commit=commit)
            db.refresh(subscription)
            return subscription, True

        return subscription, False

    def get_by_stripe_customer_id(
        self, db: Session, stripe_customer_id: str
    ) -> Optional[Subscription]:
        """Get subscription by Stripe customer ID."""
        q = select(Subscription).where(
            Subscription.stripe_customer_id == stripe_customer_id
        )
        return db.execute(q).scalar_one_or_none()

    def get_by_checkout_session_id(
        self, db: Session, checkout_session_id: str
    ) -> Optional[Subscription]:
        """Get subscription by checkout session ID."""
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
        """Upsert a subscription (create if not exists, update if exists)."""
        sub, created = self.get_or_create(
            db=db, subscription_data=subscription_data, commit=commit
        )
        if not created:
            sub = self.update(
                db=db, db_obj=sub, obj_in=subscription_data, commit=commit
            )
        return sub

    def create(
        self,
        db: Session,
        obj_in: SubscriptionCreateIn,
        commit: bool = True,
    ) -> Subscription:
        """Create new subscription."""
        orm_obj = Subscription(**obj_in.dict())
        db.add(orm_obj)
        if commit:
            db.commit()
            db.refresh(orm_obj)
        else:
            db.flush()
        return orm_obj

    def update(
        self,
        db: Session,
        db_obj: Subscription,
        obj_in: SubscriptionUpdateIn,
        commit: bool = True,
    ) -> Subscription:
        """Update existing subscription."""
        update_data = obj_in.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        if commit:
            db.commit()
            db.refresh(db_obj)
        else:
            db.flush()
        return db_obj

    def delete(self, db: Session, subscription_id: str, commit: bool = True) -> None:
        """Delete a subscription by ID."""
        subscription = self.get_by_id(db, subscription_id)
        if subscription:
            db.delete(subscription)
            if commit:
                db.commit()


# Create singleton instance for backward compatibility
subscription_repository = SubscriptionRepositoryImpl()
