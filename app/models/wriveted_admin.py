from fastapi_permissions import All, Allow
from sqlalchemy import (
    JSON,
    Column,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.mutable import MutableDict
from app.models.user import User, UserAccountType


class WrivetedAdmin(User):
    __tablename__ = "wriveted_admins"

    id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_wrivetedadmin_inherits_user"),
        primary_key=True,
    )

    __mapper_args__ = {
        "polymorphic_identity": UserAccountType.WRIVETED,
    }

    wriveted_admin_info = Column(
        MutableDict.as_mutable(JSON), nullable=True, default={}
    )

    def __repr__(self):
        active = "Active" if self.is_active else "Inactive"
        return f"<WrivetedAdmin {self.username} - {active}>"

    def __acl__(self):
        """defines who can do what to the instance
        the function returns a list containing tuples in the form of
        (Allow or Deny, principal identifier, permission name)

        If a role is not listed (like "role:user") the access will be
        automatically denied.

        (Deny, Everyone, All) is automatically appended at the end.
        """
        return [(Allow, f"user:{self.id}", All), (Allow, "role:admin", All)]
