import uuid
from datetime import datetime

from fastapi_permissions import All, Allow, Authenticated
from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import column_property, mapped_column, relationship

from app.db import Base
from app.models.student import Student


class ClassGroup(Base):
    __tablename__ = "class_groups"

    id = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    __table_args__ = (
        UniqueConstraint("name", "school_id", name="unique_class_name_per_school"),
    )

    school_id = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "schools.wriveted_identifier",
            name="fk_class_groups_school",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=True,
    )
    school = relationship("School", back_populates="class_groups", lazy="joined")
    students = relationship("Student", back_populates="class_group")

    name = mapped_column(String(256), nullable=False)

    join_code = mapped_column(String(6))

    student_count = column_property(
        select(func.count(Student.id))
        .where(Student.class_group_id == id)
        .correlate_except(Student)
        .scalar_subquery()
    )

    created_at = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    def __repr__(self):
        return f"<Class '{self.name}' ({self.school.name} - {self.student_count} students)>"

    def __acl__(self):
        """defines who can do what to the instance
        the function returns a list containing tuples in the form of
        (Allow or Deny, principal identifier, permission name)

        If a role is not listed (like "role:user") the access will be
        automatically denied.

        (Deny, Everyone, All) is automatically appended at the end.
        """
        return [
            (Allow, "role:admin", All),
            (Allow, f"educator:{self.school_id}", All),
            (Allow, f"student:{self.school_id}", "read"),
            (Allow, f"class:{self.id}", "read"),
            (Allow, Authenticated, "bind"),
        ]
