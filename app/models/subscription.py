import enum
from datetime import datetime, timedelta

from fastapi_permissions import All, Allow
from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import mapped_column, relationship

from app.db import Base


class SubscriptionProvider(str, enum.Enum):
    STRIPE = "stripe"


class SubscriptionType(str, enum.Enum):
    FAMILY = "family"
    LIBRARY = "library"
    SCHOOL = "school"


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = mapped_column(String, primary_key=True)

    parent_id = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "parents.id", name="fk_parent_stripe_subscription", ondelete="CASCADE"
        ),
        nullable=True,
        index=True,
    )
    parent = relationship("Parent", back_populates="subscription")

    # school_id = mapped_column(
    #     UUID(as_uuid=True),
    #     ForeignKey("schools.id", name="fk_school_stripe_subscription", ondelete="CASCADE"),
    #     nullable=True,
    #     index=True,
    # )
    # school = relationship("School", back_populates="subscriptions")

    type = mapped_column(
        Enum(SubscriptionType, name="enum_subscription_type"),
        nullable=False,
        default=SubscriptionType.FAMILY,
    )
    stripe_customer_id = mapped_column(String, nullable=False, index=True)

    # Note a subscription may be inactive (e.g. the user has cancelled)
    # but still have an expiration date in the future.
    is_active = mapped_column(Boolean(), default=False)
    expiration = mapped_column(
        DateTime, default=lambda: datetime.utcnow() + timedelta(days=30), nullable=False
    )
    product_id = mapped_column(
        String,
        ForeignKey("products.id", name="fk_product_stripe_subscription"),
        nullable=False,
        index=True,
    )
    product = relationship("Product", back_populates="subscriptions")

    created_at = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    info = mapped_column(MutableDict.as_mutable(JSON))
    provider = mapped_column(
        Enum(SubscriptionProvider, name="enum_subscription_provider"),
        nullable=False,
        default=SubscriptionProvider.STRIPE,
    )

    latest_checkout_session_id = mapped_column(String, nullable=True, index=True)

    def __acl__(self):
        return [
            (Allow, "role:admin", All),
            (Allow, f"user:{self.user_id}", "read"),
        ]
