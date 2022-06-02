from fastapi_permissions import All, Allow
from sqlalchemy import (
    JSON,
    Column,
    ForeignKey,
    Integer,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.mutable import MutableDict
from app.models.educator import Educator
from app.models.user import UserAccountType


class SchoolAdmin(Educator):
    """
    A concrete School Admin user in a school context.
    The primary administrator / owner of a Huey school.
    """

    __tablename__ = "school_admins"

    id = Column(
        UUID(as_uuid=True),
        ForeignKey("educators.id", name="fk_school_admin_inherits_educator"),
        primary_key=True,
    )

    __mapper_args__ = {"polymorphic_identity": UserAccountType.SCHOOL_ADMIN}

    # class_history? other misc
    school_admin_info = Column(MutableDict.as_mutable(JSON), nullable=True, default={})

    def __repr__(self):
        active = "Active" if self.is_active else "Inactive"
        return f"<School Admin {self.name} - {self.school} - {active}>"

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
            (Allow, f"educator:{self.school_id}", "read"),
            (Allow, f"schooladmin:{self.school_id}", All),
        ]
