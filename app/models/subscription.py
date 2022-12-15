import enum
from datetime import datetime

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

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_user_stripe_subscription", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    user = relationship("Parent", back_populates="subscription")

    type = Column(
        Enum(SubscriptionType, name="enum_subscription_type"),
        nullable=False,
        default=SubscriptionType.FAMILY,
    )
    stripe_customer_id = Column(String, nullable=False, index=True)
    is_active = Column(Boolean(), default=False)

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

    def __acl__(self):
        return [
            (Allow, "role:admin", All),
            (Allow, f"user:{self.user_id}", "read"),
        ]
