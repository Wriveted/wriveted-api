from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Enum
from fastapi_permissions import All, Allow
from sqlalchemy.orm import relationship
import enum

from app.db import Base


class CollectionItemReadStatus(str, enum.Enum):
    UNREAD = "UNREAD"
    TO_READ = "TO_READ"
    NOT_INTERESTED = "NOT_INTERESTED"
    READING = "READING"
    STOPPED_READING = "STOPPED_READING"
    READ = "READ"


class CollectionItemActivity(Base):
    __tablename__ = "collection_item_activity_log"

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)

    collection_item_id = Column(
        ForeignKey(
            "collection_items.id",
            name="fk_collection_item_activity_collection_item_id",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=False,
    )
    collection_item = relationship(
        "CollectionItem", lazy="joined", passive_deletes=True
    )

    reader_id = Column(
        ForeignKey("readers.id", name="fk_collection_item_activity_reader"),
        nullable=False,
    )
    reader = relationship(
        "Reader",
        back_populates="collection_item_activity_log",
        foreign_keys=[reader_id],
    )

    status = Column(
        Enum(CollectionItemReadStatus, name="enum_collection_item_read_status"),
        default=CollectionItemReadStatus.UNREAD,
        nullable=False,
        index=True,
    )

    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    # index the timestamp and reader_id together to allow for fast "current status" lookups
    Index(
        "idx_collection_item_activity_log_timestamp_reader_id",
        timestamp,
        reader_id,
    )

    def __repr__(self):
        return f"<CollectionItemActivity '{self.reader.name}' marked the book '{self.collection_item.get_display_title()}' as '{self.status}'>"

    def __acl__(self):
        return self.collection_item.__acl__()
