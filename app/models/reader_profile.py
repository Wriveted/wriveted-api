from datetime import datetime
import uuid
from sqlalchemy import JSON, Column, ForeignKey, String, Integer, func, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import relationship
from app.db import Base


class ReaderProfile(Base):
    """
    A profile for a reader belonging to a parent account (not a user entity of its own).
    """

    id = Column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        unique=True,
        primary_key=True,
        index=True,
        nullable=False,
    )

    name = Column(String, nullable=True)
    gems = Column(Integer, default=0, index=True)

    created_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    parent_id = Column(
        UUID,
        ForeignKey("parents.id", name="fk_reader_profile_parent"),
        index=True,
        nullable=True,
    )
    parent = relationship("Parent", back_populates="reader_profiles", lazy="joined")

    # preferred hues, genres, characters, reading_ability, age, last_visited, etc
    huey_attributes = Column(MutableDict.as_mutable(JSON), nullable=True, default={})
