from fastapi_permissions import All, Allow
from sqlalchemy import JSON, Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import relationship

from app.models.reader import Reader
from app.models.user import UserAccountType


class Student(Reader):
    """
    A concrete Student user in a school context.
    """

    id = Column(
        UUID(as_uuid=True),
        ForeignKey("readers.id", name="fk_student_inherits_reader", ondelete="CASCADE"),
        primary_key=True,
    )

    __mapper_args__ = {"polymorphic_identity": UserAccountType.STUDENT}

    __table_args__ = (
        UniqueConstraint(
            "username", "school_id", name="unique_student_username_per_school"
        ),
    )

    username = Column(
        String,
        index=True,
        nullable=False,
    )

    school_id = Column(
        Integer,
        ForeignKey("schools.id", name="fk_student_school", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    school = relationship("School", backref="students", foreign_keys=[school_id])

    class_group_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "class_groups.id", name="fk_student_class_group", ondelete="CASCADE"
        ),
        nullable=False,
        index=True,
    )
    class_group = relationship(
        "ClassGroup", backref="students", foreign_keys=[class_group_id]
    )

    # class_history? other misc
    student_info = Column(MutableDict.as_mutable(JSON), nullable=True, default={})

    def __repr__(self):
        active = "Active" if self.is_active else "Inactive"
        return f"<Student {self.username} - {self.school} - {active}>"

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
            (Allow, f"parent:{self.id}", All),
            (Allow, f"educator:{self.school_id}", All),
            (Allow, f"schooladmin:{self.school_id}", All),
        ]
