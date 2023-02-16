import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import mapped_column, relationship

from app.db import Base


class UserAccountType(str, enum.Enum):
    WRIVETED = "wriveted"
    STUDENT = "student"
    PUBLIC = "public"
    EDUCATOR = "educator"
    SCHOOL_ADMIN = "school_admin"
    PARENT = "parent"
    SUPPORTER = "supporter"


class User(Base):
    """
    An abstract user.

    https://docs.sqlalchemy.org/en/14/orm/inheritance.html#joined-table-inheritance
    Note: only functionally abstract (has db tables for ORM purposes, but no meaningful instantiation).
    """

    id = mapped_column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        unique=True,
        primary_key=True,
        index=True,
        nullable=False,
    )

    is_active = mapped_column(Boolean(), default=True)

    type = mapped_column(
        Enum(UserAccountType, name="enum_user_account_type"),
        nullable=False,
        index=True,
        default=UserAccountType.PUBLIC,
    )

    __mapper_args__ = {
        "polymorphic_on": type,
    }

    email = mapped_column(String, unique=True, index=True, nullable=True)

    # overall "name" string, most likely provided by SSO
    name = mapped_column(String, nullable=False)

    # Social stuff: Twitter, Goodreads
    info = mapped_column(MutableDict.as_mutable(JSON), nullable=True, default={})

    created_at = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    last_login_at = mapped_column(DateTime, nullable=True)

    collection = relationship(
        "Collection", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

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

    newsletter = mapped_column(Boolean(), nullable=False, server_default="false")
