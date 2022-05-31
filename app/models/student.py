from fastapi_permissions import All, Allow
from sqlalchemy import (
    JSON,
    Column,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import relationship
from app.models.user import User, UserAccountType


class Student(User):

    id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_student_inherits_user"),
        primary_key=True,
    )

    __mapper_args__ = {
        "polymorphic_identity": UserAccountType.STUDENT,
    }

    first_name = Column(String(30))
    last_name_initial = Column(String(1))

    school_id = Column(
        Integer,
        ForeignKey("schools.id", name="fk_admin_school"),
        nullable=True,
        index=True,
    )
    school = relationship("School", backref="students", foreign_keys=[school_id])

    # class_id = Column(
    #     UUID,
    #     ForeignKey("class_groups.id", name="fk_student_class_group"),
    #     nullable=False,
    #     index=True
    # )
    # class = relationship(
    #     "ClassGroup", backref="students", foreign_keys=[class_id]
    # )

    # Student details / preferences
    student_info = Column(MutableDict.as_mutable(JSON), nullable=True, default={})

    def __repr__(self):
        active = "Active" if self.is_active else "Inactive"
        school = f"(Student of {self.school})" if self.school else ""
        return f"<Student {self.username} - {school} - {active}>"

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
            (Allow, f"teacher:{self.school_id}", All),
        ]
