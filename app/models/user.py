import enum
import uuid
from datetime import datetime

from fastapi_permissions import All, Allow
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import relationship

from app.db import Base


class UserAccountType(str, enum.Enum):
    WRIVETED = "wriveted"
    LMS = "lms"
    LIBRARY = "library"
    STUDENT = "student"
    PUBLIC = "public"


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
    type = Column(
        Enum(UserAccountType, name="enum_user_account_type"),
        nullable=False,
        index=True,
        default=UserAccountType.PUBLIC,
    )

    school_id_as_student = Column(
        Integer,
        ForeignKey("schools.id", name="fk_student_school"),
        nullable=True,
        index=True,
    )
    school_as_student = relationship(
        "School", backref="students", foreign_keys=[school_id_as_student]
    )

    school_id_as_admin = Column(
        Integer,
        ForeignKey("schools.id", name="fk_admin_school"),
        nullable=True,
        index=True,
    )

    email = Column(String, unique=True, index=True, nullable=False)

    name = Column(String, nullable=False)

    username = Column(String, unique=True, index=True, nullable=True)

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

    def __repr__(self):
        summary = "Active" if self.is_active else "Inactive"
        if self.type == UserAccountType.WRIVETED:
            summary += " superuser "

        if self.school_id_as_admin is not None:
            summary += f" (Admin of school {self.school_id_as_admin}) "
        if self.school_as_student is not None:
            summary += f" (Student of school {self.school_as_student}) "
        return f"<User {self.name} - {summary}>"

    def __acl__(self):
        """defines who can do what to the instance
        the function returns a list containing tuples in the form of
        (Allow or Deny, principal identifier, permission name)

        If a role is not listed (like "role:user") the access will be
        automatically denied.

        (Deny, Everyone, All) is automatically appended at the end.
        """
        return [
            (Allow, f"user:{self.id}", All),
            (Allow, "role:admin", All),
            (Allow, "role:library", "read"),
        ]
