from sqlalchemy import Column, ForeignKey, String, JSON, Integer
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import relationship

from app.db import Base


class CollectionItem(Base):
    __tablename__ = "collection_items"

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)

    school_id = Column(
        ForeignKey('schools.id',
                   name="fk_collection_items_school_id"),
        index=True, nullable=False)

    edition_id = Column(
        ForeignKey('editions.id',
                   name="fk_collection_items_edition_id"),
        nullable=False)

    # Information from this particular school's LMS
    info = Column(JSON)

    copies_total = Column(Integer, default=1, nullable=False)
    copies_available = Column(Integer, default=0, nullable=False)

    # For potential future feature of "starring" certain books.
    # (say if a school gets an influx of a particular author
    # and want to encourage the group to pick one, Huey could
    # help pick from the starred subset... or something.
        # starred_pick = Column(Boolean(), default=False)

    school = relationship(
        "School",
        back_populates="collection"
    )

    # Proxy the work from the edition
    work = association_proxy('edition', 'work')
    work_id = association_proxy('edition', 'work_id')

    edition = relationship('Edition', lazy="joined")

    def __repr__(self):
        copies = f"{self.copies_available}/{self.copies_available + self.copies_on_loan}"
        return f"<CollectionItem '{self.work.title}' @ '{self.school.name}' ({copies} available)>"
