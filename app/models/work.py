import enum

from sqlalchemy import (
    Column,
    Integer,
    String,
    JSON,
    Enum
)
from sqlalchemy.orm import relationship

from app.db import Base
from app.models.author_work_association import author_work_association_table
from app.models.series_works_association import series_works_association_table


class WorkType(str, enum.Enum):
    BOOK = "book"
    PODCAST = "podcast"


class Work(Base):

    id = Column(Integer, primary_key=True, autoincrement=True)

    type = Column(Enum(WorkType), nullable=False, default=WorkType.BOOK)

    #series_id = Column(ForeignKey("series.id", name="fk_works_series_id"), nullable=True)

    # TODO may want to look at a TSVector GIN index for decent full text search
    title = Column(String(100), nullable=False, index=True)

    info = Column(JSON)

    editions = relationship('Edition', cascade="all, delete-orphan")

    series = relationship(
        "Series",
        secondary=series_works_association_table,
        back_populates="works"
    )

    # Handle Multiple Authors via a secondary association table
    authors = relationship(
        'Author',
        secondary=author_work_association_table,
        back_populates='books'
    )
