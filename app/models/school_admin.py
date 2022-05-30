from fastapi_permissions import All, Allow
from sqlalchemy import (
    JSON,
    Column,
    ForeignKey,
    Integer,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import relationship
from app.models.user import User, UserAccountType


class SchoolAdmin(User):
    __tablename__ = "school_admins"

    id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_schooladmin_inherits_user"),
        primary_key=True,
    )

    __mapper_args__ = {
        "polymorphic_identity": UserAccountType.LIBRARY,
    }

    school_id = Column(
        Integer,
        ForeignKey("schools.id", name="fk_schooladmin_school"),
        nullable=True,
        index=True,
    )
    school = relationship("School", backref="admins", foreign_keys=[school_id])

    # class_id = Column(
    #     UUID,
    #     ForeignKey("class_groups.id", name="fk_admin_class_group"),
    #     nullable=False,
    #     index=True
    # )
    # class = relationship(
    #     "ClassGroup", backref="admins", foreign_keys=[class_id]
    # )

    school_admin_info = Column(MutableDict.as_mutable(JSON), nullable=True, default={})

    def __repr__(self):
        active = "Active" if self.is_active else "Inactive"
        school = f"(Admin of {self.school})" if self.school else "(Not a school admin)"
        return f"<SchoolAdmin {self.name if self.name else self.username} - {school} - {active}>"

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
            (Allow, "role:library", All),
        ]
