import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from fastapi_permissions import Allow  # type: ignore[import-untyped]
from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.reader import Reader
from app.models.user import UserAccountType

if TYPE_CHECKING:
    from app.models.class_group import ClassGroup
    from app.models.school import School


class Student(Reader):
    """
    A concrete Student user in a school context.
    """

    __tablename__ = "students"  # type: ignore[assignment]

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("readers.id", name="fk_student_inherits_reader", ondelete="CASCADE"),
        primary_key=True,
    )

    __mapper_args__ = {"polymorphic_identity": UserAccountType.STUDENT}

    __table_args__ = (
        UniqueConstraint(
            "username", "school_id", name="uq_students_username_school_id"
        ),
    )

    username: Mapped[str] = mapped_column(
        String,
        index=True,
        nullable=False,
    )

    school_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("schools.id", name="fk_student_school", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    school: Mapped["School"] = relationship(
        "School", backref="students", foreign_keys=[school_id]
    )

    class_group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "class_groups.id", name="fk_student_class_group", ondelete="CASCADE"
        ),
        nullable=False,
        index=True,
    )
    class_group: Mapped["ClassGroup"] = relationship(
        "ClassGroup", back_populates="students", foreign_keys=[class_group_id]
    )

    # class_history? other misc
    student_info: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        MutableDict.as_mutable(JSONB),
        nullable=True,
        default={},  # type: ignore[arg-type]
    )

    def __repr__(self) -> str:
        active = "Active" if self.is_active else "Inactive"
        return f"<Student {self.username} - {self.school} - {active}>"

    async def get_principals(self) -> List[str]:
        principals = await super().get_principals()

        principals.extend(
            [
                "role:student",
                f"student:{self.school_id}",
            ]
        )

        return principals

    def __acl__(self) -> List[tuple[Any, str, Any]]:
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
