from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Enum
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
        nullable=True,
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

    def __repr__(self):
        return f"<CollectionItemActivity '{self.reader.name}' marked the book '{self.collection_item.get_display_title()}' as '{self.status}'>"

    def __acl__(self):
        """
        Defines who can do what to the CollectionItemActivity instance.
        """

        policies = [
            (Allow, "role:admin", All),
            # Allow users (or their parents) to view their own activity
            (Allow, f"user:{self.user_id}", All),
            (Allow, f"parent:{self.user_id}", "read"),
            # Educators can view school activity
            (Allow, f"educator:{self.school_id}", "read"),
        ]

        return policies
