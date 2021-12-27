from sqlalchemy import Column, ForeignKey, String, JSON, Integer
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import relationship

from app.db import Base


class CollectionItem(Base):
    __tablename__ = "collection_items"

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)

    school_id = Column(ForeignKey('schools.id', name="fk_collection_items_school_id"), index=True)
    edition_id = Column(ForeignKey('editions.id', name="fk_collection_items_edition_id"))

    # Information from this particular school's LMS
    info = Column(JSON)

    school = relationship(
        "School",
        back_populates="collection"
    )

    # Proxy the work from the edition
    work = association_proxy('edition', 'work')
    edition = relationship('Edition')

