import sqlalchemy.orm.exc
from fastapi_permissions import All, Allow
from sqlalchemy import JSON, Column, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import relationship

from app.models.user import User, UserAccountType


class Educator(User):
    """
    A concrete Educator user in a school context.
    Could be a teacher, librarian, aid, principal, etc.
    """

    id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_educator_inherits_user", ondelete="CASCADE"),
        primary_key=True,
    )

    __mapper_args__ = {"polymorphic_identity": UserAccountType.EDUCATOR}

    school_id = Column(
        Integer,
        ForeignKey("schools.id", name="fk_educator_school", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    school = relationship("School", backref="educators", foreign_keys=[school_id])

    # class_history? other misc
    educator_info = Column(MutableDict.as_mutable(JSON), nullable=True, default={})

    def __repr__(self):
        active = "Active" if self.is_active else "Inactive"
        try:
            return f"<Educator {self.name} - {self.school} - {active}>"
        except sqlalchemy.orm.exc.DetachedInstanceError:
            return f"<Educator {self.id} (detached)>"

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
            (Allow, f"schooladmin:{self.school_id}", All),
            (Allow, f"educator:{self.school_id}", "read"),
        ]
