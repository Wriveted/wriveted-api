from sqlalchemy import Column, ForeignKey, String, JSON, Integer
from sqlalchemy.orm import relationship

from app.db import Base


class CollectionItem(Base):
    __tablename__ = "collection_items"

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)

    school_id = Column(ForeignKey('schools.id', name="fk_collection_items_school_id"), index=True)

    # Note editions have composite primary keys
    work_id = Column(ForeignKey('works.id', name="fk_collection_items_work_id"), index=True)
    edition_id = Column(ForeignKey('editions.id', name="fk_collection_items_edition_id"))

    # Information from this particular school's LMS
    info = Column(JSON)

    school = relationship(
        "School",
        back_populates="collection"
    )
    work = relationship("Work")
    edition = relationship('Edition')

