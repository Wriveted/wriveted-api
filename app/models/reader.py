import uuid
from typing import List, Optional

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.common_types import user_fk
from app.models.user import User


class Reader(User):
    """
    An abstract user of Huey for reading purposes.
    Note: only functionally abstract (has db tables for ORM purposes, but no meaningful instantiation).
    """

    __mapper_args__ = {"polymorphic_identity": "reader"}

    id: Mapped[user_fk] = mapped_column(
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

    # reading_ability, age, last_visited, etc
    huey_attributes = mapped_column(
        MutableDict.as_mutable(JSON), nullable=True, default={}
    )
