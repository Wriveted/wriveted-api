from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from fastapi_permissions import All, Allow
from sqlalchemy import JSON, DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class CollectionItem(Base):
    __tablename__ = "collection_items"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, nullable=False, autoincrement=True
    )

    edition_isbn: Mapped[Optional[str]] = mapped_column(
        ForeignKey(
            "editions.isbn",
            name="fk_collection_items_edition_isbn",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=True,
    )
    edition: Mapped[Optional["Edition"]] = relationship(
        "Edition", lazy="joined", passive_deletes=True
    )
    # Proxy the work from the edition
    work: Mapped[Optional["Work"]] = association_proxy("edition", "work")
    work_id: Mapped[Optional[int]] = association_proxy("edition", "work_id")

    collection_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "collections.id",
            name="fk_collection_items_collection_id",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        index=True,
        nullable=False,
    )
    collection: Mapped["Collection"] = relationship(
        "Collection",
        back_populates="items",
        foreign_keys=[collection_id],
        passive_updates=True,
        passive_deletes=True,
    )

    activity_log: Mapped[List["CollectionItemActivity"]] = relationship(
        "CollectionItemActivity",
        back_populates="collection_item",
        cascade="all, delete-orphan",
    )

    info: Mapped[Dict] = mapped_column(MutableDict.as_mutable(JSON))

    copies_total: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    copies_available: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            collection_id, edition_isbn, name="unique_editions_per_collection"
        ),
    )

    def get_display_title(self) -> str:
        return (
            self.edition.get_display_title()
            if self.edition
            else self.info.get("title")
            if self.info
            else None
        )

    def get_cover_url(self) -> str:
        return (
            self.edition.cover_url
            if self.edition
            else self.info.get("cover_image")
            if self.info
            else None
        )

    def __repr__(self):
        return f"<CollectionItem '{self.get_display_title()}' @ '{self.collection.name}' ({self.copies_available}/{self.copies_total} available)>"

    def __acl__(self):
        """
        Defines who can do what to the CollectionItem instance.
        """
        acl = [
            (Allow, "role:admin", All),
        ]

        if self.collection.school_id is not None:
            acl.append((Allow, f"educator:{self.collection.school_id}", "read"))

        if self.collection.user_id is not None:
            acl.append((Allow, f"user:{self.collection.user_id}", All))
            acl.append((Allow, f"parent:{self.collection.user_id}", "read"))

        return acl
