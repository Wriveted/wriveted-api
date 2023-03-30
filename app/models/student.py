from fastapi_permissions import Allow
from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import mapped_column, relationship

from app.models.reader import Reader
from app.models.user import UserAccountType


class Student(Reader):
    """
    A concrete Student user in a school context.
    """

    id = mapped_column(
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

    username = mapped_column(
        String,
        index=True,
        nullable=False,
    )

    school_id = mapped_column(
        Integer,
        ForeignKey("schools.id", name="fk_student_school", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    school = relationship("School", backref="students", foreign_keys=[school_id])

    class_group_id = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "class_groups.id", name="fk_student_class_group", ondelete="CASCADE"
        ),
        nullable=False,
        index=True,
    )
    class_group = relationship(
        "ClassGroup", back_populates="students", foreign_keys=[class_group_id]
    )

    # class_history? other misc
    student_info = mapped_column(
        MutableDict.as_mutable(JSONB), nullable=True, default={}
    )

    def __repr__(self):
        active = "Active" if self.is_active else "Inactive"
        return f"<Student {self.username} - {self.school} - {active}>"

    def get_principals(self):
        principals = super().get_principals()

        principals.extend(
            [
                "role:student",
                f"student:{self.school_id}",
            ]
        )

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
                (Allow, f"educator:{self.school_id}", "all-school"),
                (Allow, f"schooladmin:{self.school_id}", "all-school"),
            ]
        )

        return acl
