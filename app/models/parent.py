from typing import Dict, Optional

from fastapi_permissions import Allow
from sqlalchemy import JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import mapped_column, relationship, Mapped
from app.models.subscription import Subscription
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.common_types import user_fk
from app.models.user import User, UserAccountType


class Parent(User):
    """
    A concrete Parent of Students or PublicReaders.
    """

    id: Mapped[user_fk] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_parent_inherits_user", ondelete="CASCADE"),
        primary_key=True,
    )

    __mapper_args__ = {"polymorphic_identity": UserAccountType.PARENT}

    # backref:
    # children = relationship("Reader")

    # misc
    parent_info: Mapped[Optional[Dict]] = mapped_column(
        MutableDict.as_mutable(JSON), nullable=True, default={}
    )

    subscription: Mapped[Optional["Subscription"]] = relationship(
        "Subscription",
        back_populates="parent",
        uselist=False,
        cascade="all, delete-orphan",
    )

    readers = relationship(
        "Reader",
        back_populates="parent",
        foreign_keys="Reader.parent_id",
    )

    # misc
    parent_info = mapped_column(MutableDict.as_mutable(JSON), nullable=True, default={})

    def __repr__(self):
        active = "Active" if self.is_active else "Inactive"
        return f"<Parent {self.name} - {self.children} - {active}>"

    def get_principals(self):
        principals = super().get_principals()

        if self.children:
            principals.extend([f"parent:{child.id}" for child in self.children])

        return principals

    def __acl__(self):
        """defines who can do what to the instance
        the function returns a list containing tuples in the form of
        (Allow or Deny, principal identifier, permission name)
        If a role is not listed (like "role:user") the access will be
        automatically denied.
        (Deny, Everyone, All) is automatically appended at the end.
        """
        acl = super().__acl__()

        acl.extend(
            [
                (Allow, f"child:{self.id}", "read"),
            ]
        )

        return acl
