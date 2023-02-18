import enum
import uuid
from datetime import datetime

from fastapi_permissions import All, Allow

from sqlalchemy import JSON, Boolean, DateTime, Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import mapped_column, relationship, Mapped

from app.db import Base
from app.models.supporter_reader_association import SupporterReaderAssociation


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

    @hybrid_property
    def phone(self):
        return self.info.get("phone")

    # overall "name" string, most likely provided by SSO
    name = mapped_column(String, nullable=False)

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

    # targeting the association instead of the users directly to
    # include the "active" status in any outputs
    supportee_associations: Mapped[list[SupporterReaderAssociation]] = relationship(
        SupporterReaderAssociation,
        back_populates="supporter",
    )

    def get_principals(self):
        principals = [f"user:{self.id}"]

        for association in self.supportee_associations:
            if association.is_active:
                principals.append(f"supporter:{association.id}")

        return principals

    def __acl__(self):
        """defines who can do what to the instance
        the function returns a list containing tuples in the form of
        (Allow or Deny, principal identifier, permission name)
        If a role is not listed (like "role:user") the access will be
        automatically denied.
        (Deny, Everyone, All) is automatically appended at the end.
        """
        acl = [
            (Allow, f"user:{self.id}", All),
            (Allow, "role:admin", All),
            (Allow, f"supportee:{self.id}", "notify"),
        ]

        return acl
