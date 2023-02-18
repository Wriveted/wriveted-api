from fastapi_permissions import All, Allow
from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.parent import Parent
from app.models.supporter_reader_association import SupporterReaderAssociation
from app.models.user import User


class Reader(User):
    """
    An abstract user of Huey for reading purposes.
    Note: only functionally abstract (has db tables for ORM purposes, but no meaningful instantiation).
    """

    __mapper_args__ = {"polymorphic_identity": "reader"}

    id = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_reader_inherits_user", ondelete="CASCADE"),
        primary_key=True,
    )

    first_name = mapped_column(String, nullable=True)
    last_name_initial = mapped_column(String, nullable=True)

    collection_item_activity_log = relationship(
        "CollectionItemActivity", back_populates="reader"
    )

    parent_id = mapped_column(
        UUID,
        ForeignKey("parents.id", name="fk_reader_parent"),
        nullable=True,
        index=True,
    )
    parent: Mapped["Parent"] = relationship(
        "Parent", backref="children", foreign_keys=[parent_id]
    )

    # targeting the association instead of the users directly to
    # include the "active" status in any outputs
    supporter_associations: Mapped[list[SupporterReaderAssociation]] = relationship(
        SupporterReaderAssociation,
        back_populates="reader",
    )

    # reading_ability, age, last_visited, etc
    huey_attributes = mapped_column(
        MutableDict.as_mutable(JSON), nullable=True, default={}
    )

    def get_principals(self):
        principals = super().get_principals()

        principals.append("role:reader")
        if self.parent:
            principals.append(f"child:{self.parent_id}")

        return principals

    def __acl__(self):
        acl = super().__acl__()

        acl.extend(
            [
                (Allow, f"parent:{self.id}", All),
                (Allow, f"supporter:{self.id}", "support"),
            ]
        )

        return acl
