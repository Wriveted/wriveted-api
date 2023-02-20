import enum
import uuid
from datetime import datetime
from typing import Dict, Optional

from fastapi_permissions import All, Allow
from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class EventLevel(str, enum.Enum):
    DEBUG = "debug"
    NORMAL = "normal"
    WARNING = "warning"
    ERROR = "error"


class EventSlackChannel(str, enum.Enum):
    GENERAL = "#api-alerts"
    MEMBERSHIPS = "#memberships"


class Event(Base):
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), default=uuid.uuid4, primary_key=True
    )

    # This is really the event name (like in Mixpanel)
    title: Mapped[str] = mapped_column(String(256), nullable=False, index=True)

    # Any properties for the event
    info: Mapped[Optional[Dict]] = mapped_column(
        MutableDict.as_mutable(JSON), nullable=True
    )

    @hybrid_property
    def description(self):
        return self.info["description"]

    level: Mapped[EventLevel] = mapped_column(
        Enum(EventLevel), nullable=False, default=EventLevel.NORMAL
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )

    # These are optional
    school_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("schools.id", name="fk_event_school"), nullable=True
    )
    school: Mapped[Optional["School"]] = relationship(
        "School", back_populates="events", foreign_keys=[school_id]
    )

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", name="fk_event_user"), nullable=True
    )
    user: Mapped[Optional["User"]] = relationship(
        "User", back_populates="events", foreign_keys=[user_id]
    )

    # Partial indexes for school and user events

    __table_args__ = (
        Index("ix_events_school", "school_id", postgresql_where=school_id.is_not(None)),
        Index("ix_events_user", "user_id", postgresql_where=user_id.is_not(None)),
    )

    service_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("service_accounts.id", name="fk_event_service_account"),
        nullable=True,
    )
    service_account: Mapped[Optional["ServiceAccount"]] = relationship(
        "ServiceAccount", foreign_keys=[service_account_id], back_populates="events"
    )

    def __repr__(self):
        return f"<Event {self.title} - {self.description}>"

    def __acl__(self):
        acl = [
            (Allow, "role:admin", All),
        ]

        if self.school_id is not None:
            acl.append((Allow, f"educator:{self.school_id}", "read"))
            # acl.append((Allow, f"student:{self.school_id}", "read"))

        if self.user_id is not None:
            acl.append((Allow, f"user:{self.user_id}", "read"))

            acl.append((Allow, f"parent:{self.user_id}", "read"))

        return acl
