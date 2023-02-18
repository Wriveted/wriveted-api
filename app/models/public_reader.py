from typing import Dict

from fastapi_permissions import All, Allow
from sqlalchemy import JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column

from app.db.common_types import user_fk
from app.models.reader import Reader
from app.models.user import UserAccountType


class PublicReader(Reader):
    """
    A concrete Reader user in public context (home/library).
    """

    __tablename__ = "public_readers"

    id: Mapped[user_fk] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "readers.id", name="fk_public_reader_inherits_reader", ondelete="CASCADE"
        ),
        primary_key=True,
    )

    __mapper_args__ = {"polymorphic_identity": UserAccountType.PUBLIC}

    # misc
    reader_info: Mapped[Dict] = mapped_column(
        MutableDict.as_mutable(JSON), nullable=True, default={}
    )

    def __repr__(self):
        active = "Active" if self.is_active else "Inactive"
        return f"<Public Reader {self.name} - {active}>"

    def get_principals(self):
        principals = super().get_principals()
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
        return acl
