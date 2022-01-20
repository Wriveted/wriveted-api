import enum
import uuid

from sqlalchemy import (
    Column,
    Integer,
    Enum,
    DateTime,
    JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db import Base


class JobType(str, enum.Enum):
    POPULATE = "Populate"
    UPDATE = "Update"


class JobStatus(str, enum.Enum):
    PENDING = "Pending"
    RUNNING = "Running"
    COMPLETE = "Complete"


class DbJob(Base):
    __tablename__ = 'db_jobs'
    id = Column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        primary_key=True
    )

    job_type = Column(Enum(JobType), nullable=False)

    job_status = Column(Enum(JobStatus), nullable=False, default=JobStatus.PENDING)

    summary = Column(JSON(), nullable=True)

    total_items = Column(Integer)

    successes = Column(Integer)

    errors = Column(Integer)

    events = relationship("Event", back_populates='db_job', cascade="all, delete-orphan")

    created_timestamp = Column(DateTime)

    started_timestamp = Column(DateTime)

    ended_timestamp = Column(DateTime)

    def __repr__(self):
        return f"<Event {self.title} - {self.description}>"
