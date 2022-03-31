import enum
import uuid

from sqlalchemy import Column, ForeignKey, Integer, Enum, DateTime, JSON, func
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
    FAILED = "Failed"


class DbJob(Base):
    __tablename__ = "db_jobs"
    id = Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True)

    type = Column(Enum(JobType), nullable=False)

    status = Column(Enum(JobStatus), nullable=False, default=JobStatus.PENDING)

    summary = Column(JSON(), nullable=True)

    total_items = Column(Integer)

    successes = Column(Integer)

    errors = Column(Integer)

    created_timestamp = Column(DateTime, server_default=func.now())

    started_timestamp = Column(DateTime, nullable=True)

    ended_timestamp = Column(DateTime, nullable=True)

    school_id = Column(
        Integer,
        ForeignKey("schools.id", name="fk_db_jobs_schools"),
        index=True,
        nullable=False,
    )
    school = relationship("School", back_populates="db_jobs", lazy="selectin")

    def __repr__(self):
        return f"<Event {self.type} - {self.status}>"
