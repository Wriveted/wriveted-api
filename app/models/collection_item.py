from sqlalchemy import Column, ForeignKey, Index, String, JSON, Integer, UniqueConstraint
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

    Index("index_editions_per_collection", school_id, edition_id, unique=True)
    #UniqueConstraint(school_id, edition_id, name="unique_editions_per_collection")

    # Information from this particular school's LMS
    info = Column(JSON)

    copies_available = Column(Integer, default=1, nullable=False)
    copies_on_loan = Column(Integer, default=0, nullable=False)

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
