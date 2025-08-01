from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import UUID

from fastapi_permissions import All, Allow  # type: ignore[import-untyped]
from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.collection import Collection
    from app.models.collection_item_activity import CollectionItemActivity
    from app.models.edition import Edition
    from app.models.work import Work


class CollectionItem(Base):
    __tablename__ = "collection_items"  # type: ignore[assignment]

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
    work: Any = association_proxy("edition", "work")
    work_id: Any = association_proxy("edition", "work_id")

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

    info: Mapped[Optional[Dict]] = mapped_column(MutableDict.as_mutable(JSONB))  # type: ignore[arg-type]

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

    def get_display_title(self) -> str | None:
        return (
            self.edition.get_display_title()
            if self.edition
            else self.info.get("title")
            if self.info
            else None
        )

    def get_cover_url(self) -> str | None:
        return (
            self.edition.cover_url
            if self.edition
            else self.info.get("cover_image")
            if self.info
            else None
        )

    def __repr__(self) -> str:
        return f"<CollectionItem '{self.get_display_title()}' @ '{self.collection.name}' ({self.copies_available}/{self.copies_total} available)>"

    def __acl__(self) -> List[tuple[Any, str, str]]:
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
