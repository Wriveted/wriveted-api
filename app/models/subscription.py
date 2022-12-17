import enum
from datetime import datetime, timedelta

from fastapi_permissions import All, Allow
from sqlalchemy import JSON, Boolean, Column, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import relationship

from app.db import Base


class SubscriptionProvider(str, enum.Enum):
    STRIPE = "stripe"


class SubscriptionType(str, enum.Enum):
    FAMILY = "family"
    LIBRARY = "library"
    SCHOOL = "school"


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(String, primary_key=True)

    parent_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "parents.id", name="fk_parent_stripe_subscription", ondelete="CASCADE"
        ),
        nullable=True,
        index=True,
    )
    parent = relationship("Parent", back_populates="subscription")

    # school_id = Column(
    #     UUID(as_uuid=True),
    #     ForeignKey("schools.id", name="fk_school_stripe_subscription", ondelete="CASCADE"),
    #     nullable=True,
    #     index=True,
    # )
    # school = relationship("School", back_populates="subscriptions")

    type = Column(
        Enum(SubscriptionType, name="enum_subscription_type"),
        nullable=False,
        default=SubscriptionType.FAMILY,
    )
    stripe_customer_id = Column(String, nullable=False, index=True)

    # Note a subscription may be in_active (e.g. the user has cancelled)
    # but still have an expiration date in the future.
    is_active = Column(Boolean(), default=False)
    expiration = Column(
        DateTime, default=lambda: datetime.utcnow() + timedelta(days=30), nullable=False
    )
    product_id = Column(
        String,
        ForeignKey("products.id", name="fk_product_stripe_subscription"),
        nullable=False,
        index=True,
    )
    product = relationship("Product", back_populates="subscriptions")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    info = Column(MutableDict.as_mutable(JSON))
    provider = Column(
        Enum(SubscriptionProvider, name="enum_subscription_provider"),
        nullable=False,
        default=SubscriptionProvider.STRIPE,
    )

    latest_checkout_session_id = Column(String, nullable=True, index=True)

    def __acl__(self):
        return [
            (Allow, "role:admin", All),
            (Allow, f"user:{self.user_id}", "read"),
        ]
