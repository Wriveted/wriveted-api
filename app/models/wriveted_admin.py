import uuid
from typing import Dict

from fastapi_permissions import All, Allow
from sqlalchemy import JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column

from app.models.user import User, UserAccountType


class WrivetedAdmin(User):
    """
    A concrete Wriveted Admin.
    """

    __tablename__ = "wriveted_admins"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id", name="fk_wriveted_admin_inherits_user", ondelete="CASCADE"
        ),
        primary_key=True,
    )

    __mapper_args__ = {"polymorphic_identity": UserAccountType.WRIVETED}

    # misc
    wriveted_admin_info: Mapped[Dict] = mapped_column(
        MutableDict.as_mutable(JSON), nullable=True, default={}
    )

    def __repr__(self):
        active = "Active" if self.is_active else "Inactive"
        return f"<Wriveted Admin {self.name} - {active}>"

    def get_principals(self):
        principals = super().get_principals()
        principals.append("role:admin")
        return principals
