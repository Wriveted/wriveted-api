import uuid
from typing import TYPE_CHECKING, Any, List, Optional

from fastapi_permissions import All, Allow  # type: ignore[import-untyped]
from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.user import User

if TYPE_CHECKING:
    from app.models.collection_item_activity import CollectionItemActivity
    from app.models.parent import Parent
    from app.models.supporter_reader_association import SupporterReaderAssociation


class Reader(User):
    """
    An abstract user of Huey for reading purposes.
    Note: only functionally abstract (has db tables for ORM purposes, but no meaningful instantiation).
    """

    __mapper_args__ = {"polymorphic_identity": "reader"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_reader_inherits_user", ondelete="CASCADE"),
        primary_key=True,
    )

    first_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_name_initial: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    collection_item_activity_log: Mapped[List["CollectionItemActivity"]] = relationship(
        "CollectionItemActivity", back_populates="reader"
    )

    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID,
        ForeignKey("parents.id", name="fk_reader_parent"),
        nullable=True,
        index=True,
    )
    parent: Mapped[Optional["Parent"]] = relationship(
        "Parent", backref="children", foreign_keys=[parent_id]
    )

    # targeting the association instead of the users directly to
    # include the "active" status in any outputs
    supporter_associations: Mapped[list["SupporterReaderAssociation"]] = relationship(
        "SupporterReaderAssociation",
        back_populates="reader",
    )

    # reading_ability, age, last_visited, etc
    huey_attributes: Mapped[Optional[dict]] = mapped_column(
        MutableDict.as_mutable(JSONB), nullable=True, default={}  # type: ignore[arg-type]
    )

    async def get_principals(self) -> List[str]:
        principals = await super().get_principals()

        principals.append("role:reader")

        if self.parent_id is not None:
            principals.append(f"child:{self.parent_id}")

        return principals

    def __acl__(self) -> List[tuple[Any, str, str]]:
        acl = super().__acl__()

        acl.extend(
            [
                (Allow, f"parent:{self.id}", All),
                (Allow, f"supporter:{self.id}", "support"),
            ]
        )

        return acl
