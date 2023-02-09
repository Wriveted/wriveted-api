import enum
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import JSON, Boolean, DateTime, Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.db.common_types import user_fk


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

    https://docs.sqlalchemy.org/en/14/orm/inheritance.html#joined-table-inheritance
    Note: only functionally abstract (has db tables for ORM purposes, but no meaningful instantiation).
    """

    id: Mapped[user_fk] = mapped_column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        unique=True,
        primary_key=True,
        index=True,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(Boolean(), default=True)

    type: Mapped[UserAccountType] = mapped_column(
        Enum(UserAccountType, name="enum_user_account_type"),
        nullable=False,
        index=True,
        default=UserAccountType.PUBLIC,
    )

    __mapper_args__ = {
        "polymorphic_on": type,
    }

    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=True)

    # overall "name" string, most likely provided by SSO
    name: Mapped[str] = mapped_column(String, nullable=False)

    # Social stuff: Twitter, Goodreads
    info: Mapped[Dict] = mapped_column(
        MutableDict.as_mutable(JSON), nullable=True, default={}
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    last_login_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    collection: Mapped[Optional["Collection"]] = relationship(
        "Collection", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    booklists: Mapped[List["BookList"]] = relationship(
        "BookList",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    events: Mapped[List["Event"]] = relationship(
        "Event",
        lazy="dynamic",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="desc(Event.timestamp)",
    )

    newsletter: Mapped[bool] = mapped_column(
        Boolean(), nullable=False, server_default="false"
    )
