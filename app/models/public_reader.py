from fastapi_permissions import All, Allow
from sqlalchemy import (
    JSON,
    Column,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.mutable import MutableDict

from app.models.reader import Reader
from app.models.user import UserAccountType


class PublicReader(Reader):
    """
    A concrete Reader user in public context (home/library).
    """

    __tablename__ = "public_readers"

    id = Column(
        UUID(as_uuid=True),
        ForeignKey("readers.id", name="fk_public_reader_inherits_reader"),
        primary_key=True,
    )

    __mapper_args__ = {"polymorphic_identity": UserAccountType.PUBLIC}

    # misc
    reader_info = Column(MutableDict.as_mutable(JSON), nullable=True, default={})

    def __repr__(self):
        active = "Active" if self.is_active else "Inactive"
        return f"<Public Reader {self.username} - {active}>"

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
        ]
