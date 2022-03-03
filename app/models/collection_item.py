from sqlalchemy import (
    Column,
    ForeignKey,
    Index,
    String,
    JSON,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import relationship

from app.db import Base


class CollectionItem(Base):
    __tablename__ = "collection_items"

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)

    school_id = Column(
        ForeignKey("schools.id", name="fk_collection_items_school_id"),
        index=True,
        nullable=False,
    )

    edition_isbn = Column(
        ForeignKey("editions.isbn", name="fk_collection_items_edition_isbn"),
        nullable=False,
    )

    Index("index_editions_per_collection", school_id, edition_isbn, unique=True)
    # UniqueConstraint(school_id, edition_id, name="unique_editions_per_collection")

    # Information from this particular school's LMS
    info = Column(MutableDict.as_mutable(JSON))

    copies_total = Column(Integer, default=1, nullable=False)
    copies_available = Column(Integer, default=0, nullable=False)

    # For potential future feature of "starring" certain books.
    # (say if a school gets an influx of a particular author
    # and want to encourage the group to pick one, Huey could
    # help pick from the starred subset... or something.
    # starred_pick = Column(Boolean(), default=False)

    school = relationship("School", back_populates="collection")

    # Proxy the work from the edition
    work = association_proxy("edition", "work")
    work_id = association_proxy("edition", "work_id")

    edition = relationship("Edition", lazy="joined")

    def __repr__(self):
        return f"<CollectionItem '{self.work.title}' @ '{self.school.name}' ({self.copies_available}/{self.copies_total} available)>"
