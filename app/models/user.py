import uuid
from datetime import datetime

from sqlalchemy import (
    Column,

    String,
    JSON,
    DateTime, Boolean, ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db import Base


class User(Base):

    id = Column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        unique=True,
        primary_key=True,
        index=True,
        nullable=False,
    )
    is_active = Column(Boolean(), default=True)

    school_id = Column(ForeignKey('schools.id', name="fk_event_school"), nullable=True)
    school = relationship("School", back_populates='users')

    is_superuser = Column(Boolean(), default=False)

    email = Column(String, unique=True, index=True, nullable=False)

    name = Column(String, nullable=False)

    # Social stuff: Twitter, Goodreads
    info = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    events = relationship("Event", back_populates='user')
