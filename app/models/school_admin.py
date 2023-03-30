from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import mapped_column

from app.models.educator import Educator
from app.models.user import UserAccountType


class SchoolAdmin(Educator):
    """
    A concrete School Admin user in a school context.
    The primary administrator / owner of a Huey school.
    """

    __tablename__ = "school_admins"

    id = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "educators.id", name="fk_school_admin_inherits_educator", ondelete="CASCADE"
        ),
        primary_key=True,
    )

    __mapper_args__ = {"polymorphic_identity": UserAccountType.SCHOOL_ADMIN}

    # class_history? other misc
    school_admin_info = mapped_column(
        MutableDict.as_mutable(JSONB), nullable=True, default={}
    )

    def __repr__(self):
        active = "Active" if self.is_active else "Inactive"
        return f"<School Admin {self.name} - {self.school} - {active}>"

    def get_principals(self):
        principals = super().get_principals()
        principals.append(f"schooladmin:{self.school_id}")
        return principals
