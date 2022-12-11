from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import relationship
from app.db import Base
from fastapi_permissions import All, Allow


class StripeSubscription(Base):
    __tablename__ = "stripe_subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_user_stripe_subscription"),
        nullable=False,
        index=True,
    )
    user = relationship("User", back_populates="stripe_subscription")

    stripe_customer_id = Column(String, nullable=False, index=True)
    is_active = Column(Boolean(), default=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    info = Column(MutableDict.as_mutable(JSON))

    def __acl__(self):
        return [
            (Allow, "role:admin", All),
            (Allow, "role:stripe", All),
        ]
