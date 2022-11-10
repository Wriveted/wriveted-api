from datetime import datetime
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, Integer, func
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import relationship

from app.db import Base


class CollectionItem(Base):
    __tablename__ = "collection_items"

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)

    edition_isbn = Column(
        ForeignKey("editions.isbn", name="fk_collection_items_edition_isbn"),
        index=True,
        nullable=False,
    )
    edition = relationship("Edition", lazy="joined")
    # Proxy the work from the edition
    work = association_proxy("edition", "work")
    work_id = association_proxy("edition", "work_id")

    collection_id = Column(
        ForeignKey(
            "collections.id",
            name="fk_collection_items_collection_id",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=False,
    )
    collection = relationship(
        "Collection", back_populates="items", foreign_keys=[collection_id]
    )

    Index("index_editions_per_collection", collection_id, edition_isbn, unique=True)

    info = Column(MutableDict.as_mutable(JSON))

    copies_total = Column(Integer, default=1, nullable=False)
    copies_available = Column(Integer, default=1, nullable=False)

    created_at = Column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    def __repr__(self):
        return f"<CollectionItem '{self.work.title}' @ '{self.collection.name}' ({self.copies_available}/{self.copies_total} available)>"
