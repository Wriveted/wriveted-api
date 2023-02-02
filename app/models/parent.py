from fastapi_permissions import All, Allow
from sqlalchemy import JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import mapped_column, relationship

from app.models.user import User, UserAccountType


class Parent(User):
    """
    A concrete Parent of Students or PublicReaders.
    """

    id = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_parent_inherits_user", ondelete="CASCADE"),
        primary_key=True,
    )

    __mapper_args__ = {"polymorphic_identity": UserAccountType.PARENT}

    # backref:
    # children = relationship("Reader")

    # misc
    parent_info = mapped_column(MutableDict.as_mutable(JSON), nullable=True, default={})

    subscription = relationship(
        "Subscription",
        back_populates="parent",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        active = "Active" if self.is_active else "Inactive"
        return f"<Parent {self.name} - {self.children} - {active}>"

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
            (Allow, f"child:{self.id}", "read"),
        ]
