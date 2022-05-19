import enum
import uuid
from datetime import datetime

from fastapi_permissions import Allow, All
from sqlalchemy import JSON, Column, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import relationship

from app.db import Base


class EventLevel(str, enum.Enum):
    DEBUG = "debug"
    NORMAL = "normal"
    WARNING = "warning"
    ERROR = "error"


class Event(Base):
    id = Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True)

    # This is really the event name (like in Mixpanel)
    title = Column(String(256), nullable=False, index=True)

    # Any properties for the event
    info = Column(MutableDict.as_mutable(JSON), nullable=True)

    @hybrid_property
    def description(self):
        return self.info["description"]

    level = Column(Enum(EventLevel), nullable=False, default=EventLevel.NORMAL)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # These are optional
    school_id = Column(ForeignKey("schools.id", name="fk_event_school"), nullable=True)
    school = relationship("School", back_populates="events", foreign_keys=[school_id])

    user_id = Column(ForeignKey("users.id", name="fk_event_user"), nullable=True)
    user = relationship("User", back_populates="events", foreign_keys=[user_id])

    service_account_id = Column(
        ForeignKey("service_accounts.id", name="fk_event_service_account"),
        nullable=True,
    )
    service_account = relationship(
        "ServiceAccount", foreign_keys=[service_account_id], back_populates="events"
    )

    def __repr__(self):
        return f"<Event {self.title} - {self.description}>"


    def __acl__(self):
        acl = [
            (Allow, "role:admin", All),
        ]

        if self.school_id is not None:
            acl.append((Allow, f"teacher:{self.school_id}", "read"))
            #acl.append((Allow, f"student:{self.school_id}", "read"))

        if self.user_id is not None:
            acl.append((Allow, f"user:{self.user_id}", "read"))

        return acl