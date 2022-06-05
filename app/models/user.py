import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import relationship

from app.db import Base


class UserAccountType(str, enum.Enum):
    WRIVETED = "wriveted"
    STUDENT = "student"
    PUBLIC = "public"
    EDUCATOR = "educator"
    SCHOOL_ADMIN = "school_admin"
    PARENT = "parent"


class User(Base):
    """
    An abstract user.
    Note: only functionally abstract (has db tables for ORM purposes, but no meaningful instantiation).
    """

    id = Column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        unique=True,
        primary_key=True,
        index=True,
        nullable=False,
    )

    is_active = Column(Boolean(), default=True)

    type = Column(
        Enum(UserAccountType, name="enum_user_account_type"),
        nullable=False,
        index=True,
        default=UserAccountType.PUBLIC,
    )

    __mapper_args__ = {
        "polymorphic_on": type,
    }

    email = Column(String, unique=True, index=True, nullable=True)

    # overall "name" string, most likely provided by SSO
    name = Column(String, nullable=False)

    # Social stuff: Twitter, Goodreads
    info = Column(MutableDict.as_mutable(JSON), nullable=True, default={})

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    last_login_at = Column(DateTime, nullable=True)

    booklists = relationship(
        "BookList",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    events = relationship(
        "Event",
        lazy="dynamic",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="desc(Event.timestamp)",
    )

    newsletter = Column(Boolean(), nullable=False, server_default="false")
