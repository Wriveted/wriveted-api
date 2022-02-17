import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    Enum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db import Base


class EventLevel(str, enum.Enum):
    DEBUG = "debug"
    NORMAL = "normal"
    WARNING = "warning"
    ERROR = "error"


class Event(Base):
    id = Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True)
    title = Column(String(256), nullable=False)
    description = Column(String(), nullable=False, default="")

    level = Column(
        Enum(EventLevel), nullable=False, default=EventLevel.NORMAL, index=True
    )
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

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

    db_job_id = Column(ForeignKey("db_jobs.id", name="fk_event_db_job"), nullable=True)
    db_job = relationship("DbJob", foreign_keys=[db_job_id], back_populates="events")

    def __repr__(self):
        return f"<Event {self.title} - {self.description}>"
