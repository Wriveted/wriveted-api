from sqlalchemy import (
    Column,
    Computed,
    ForeignKey,
    Integer,
    String,
    JSON,
    Enum
)
from sqlalchemy.orm import relationship
from app.db import Base
from app.models.author_work_association import author_work_association_table

import enum


class WorkType(str, enum.Enum):
    BOOK = "book"
    PODCAST = "podcast"


class Work(Base):

    id = Column(String(36), primary_key=True, nullable=False)
    type = Column(Enum(WorkType), nullable=False, default=WorkType.BOOK)

    series_id = Column(String(36), ForeignKey("series.id", name="FK_Editions_Works"), nullable=True)

    title = Column(String(100), nullable=False)
    info = Column(JSON)

    editions = relationship('Edition', cascade="all, delete-orphan")

    # Handle Multiple Authors via a secondary association table
    series = relationship("Series", back_populates="works")

    authors = relationship(
        'Author',
        secondary=author_work_association_table,
        back_populates='books'
    )
