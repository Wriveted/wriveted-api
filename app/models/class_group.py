import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional

from fastapi_permissions import (  # type: ignore[import-untyped]
    All,
    Allow,
    Authenticated,
)
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
from sqlalchemy.orm import Mapped, column_property, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.school import School
    from app.models.student import Student
else:
    from app.models.student import Student


class ClassGroup(Base):
    __tablename__ = "class_groups"  # type: ignore[assignment]

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    __table_args__ = (
        UniqueConstraint("name", "school_id", name="uq_class_groups_name_school_id"),
    )

    school_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "schools.wriveted_identifier",
            name="fk_class_groups_school",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=True,
    )
    school: Mapped[Optional["School"]] = relationship(
        "School", back_populates="class_groups", lazy="joined"
    )
    students: Mapped[List["Student"]] = relationship(
        "Student", back_populates="class_group"
    )

    name: Mapped[str] = mapped_column(String(256), nullable=False)

    join_code: Mapped[Optional[str]] = mapped_column(String(6))

    student_count: Mapped[int] = column_property(
        select(func.count(Student.id))
        .where(Student.class_group_id == id)
        .correlate_except(Student)
        .scalar_subquery()
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Optional association with primary teacher
    # Info blob where we can store the ordered class level, e.g. Year 0, 1 - 13 in NZ
    # and K1, K2 ... in Aus.

    def __repr__(self) -> str:
        school_name = self.school.name if self.school else "Unknown"
        return f"<Class '{self.name}' ({school_name} - {self.student_count} students)>"

    def __acl__(self) -> List[tuple[Any, str, Any]]:
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
