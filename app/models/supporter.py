from fastapi_permissions import All, Allow
from sqlalchemy import JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import mapped_column, Mapped, relationship
from app.models.parent import Parent
from app.models.reader import Reader
from app.models.supporter_reader_association import SupporterReaderAssociation
from app.models.user import User, UserAccountType
from sqlalchemy.ext.hybrid import hybrid_property


class Supporter(User):
    """
    A concrete Supporter of a Reader.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_supporter_inherits_user", ondelete="CASCADE"),
        primary_key=True,
    )

    __mapper_args__ = {"polymorphic_identity": UserAccountType.SUPPORTER}

    @hybrid_property
    def phone(self):
        return self.info["phone"]

    parent_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("parents.id", name="fk_supporter_parent"),
        nullable=False,
        index=True,
    )
    parent: Mapped[Parent] = relationship(
        "Parent", back_populates="reader_supporters", foreign_keys=[parent_id]
    )

    readers: Mapped[list[Reader]] = relationship(
        "Reader",
        secondary=SupporterReaderAssociation.__table__,
        back_populates="supporters",
    )

    # misc
    supporter_info = mapped_column(
        MutableDict.as_mutable(JSON), nullable=True, default={}
    )

    def __repr__(self):
        active = "Active" if self.is_active else "Inactive"
        return f"<Supporter {self.name} - {active}>"

    def __acl__(self):
        """defines who can do what to the instance
        the function returns a list containing tuples in the form of
        (Allow or Deny, principal identifier, permission name)
        If a role is not listed (like "role:user") the access will be
        automatically denied.
        (Deny, Everyone, All) is automatically appended at the end.
        """
        roles = [
            (Allow, f"user:{self.id}", All),
            (Allow, f"user:{self.parent_id}", "All"),
            (Allow, "role:admin", All),
        ]
        if self.parent_id:
            roles.append((Allow, f"user:{self.parent_id}", All))

        return roles
