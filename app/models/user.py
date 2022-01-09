import uuid
from datetime import datetime

from sqlalchemy import (
    Column,

    String,
    JSON,
    DateTime, Boolean, ForeignKey,
)
from sqlalchemy.ext.mutable import MutableDict
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

    school_id = Column(ForeignKey('schools.id', name="fk_user_school"), nullable=True)
    school = relationship("School", back_populates='users')

    is_superuser = Column(Boolean(), default=False)

    email = Column(String, unique=True, index=True, nullable=False)

    name = Column(String, nullable=False)

    # Social stuff: Twitter, Goodreads
    info = Column(MutableDict.as_mutable(JSON), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    events = relationship("Event", back_populates='user', cascade="all, delete-orphan")

    def __repr__(self):
        summary = "Active" if self.is_active else "Inactive"
        if self.is_superuser:
            summary += " superuser "

        if self.school_id is not None:
            summary += f" (linked to school {self.school_id}) "
        return f"<User {self.name} - {summary}>"
