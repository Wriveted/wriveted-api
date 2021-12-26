from sqlalchemy import Column, ForeignKey, String, JSON
from sqlalchemy.orm import relationship

from app.db import Base


class CollectionItem(Base):
    __tablename__ = "collection_items"

    school_id = Column(String(36), ForeignKey('schools.id'), index=True)

    # Note editions have composite primary keys
    work_id = Column(String(36), ForeignKey('works.id'))
    edition_id = Column(String(36), ForeignKey('editions.id'))

    # Information from this particular school's LMS
    info = Column(JSON)


    school = relationship(
        "School",
        back_populates="collection"
    )
    work = relationship("Work")
    edition = relationship('Edition')