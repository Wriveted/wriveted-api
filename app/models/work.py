import enum

from sqlalchemy import (
    Column,
    Integer,
    String,
    JSON,
    Enum,
    Boolean,
    DateTime,
    Text,
    Computed,
    null,
)
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import relationship
from sqlalchemy.ext.mutable import MutableDict

from app.db import Base
from app.models.author_work_association import author_work_association_table
from app.models.series_works_association import series_works_association_table
from app.models.booklist_work_association import booklist_work_association_table


class WorkType(str, enum.Enum):
    BOOK = "book"
    PODCAST = "podcast"


class Work(Base):

    id = Column(Integer, primary_key=True, autoincrement=True)

    type = Column(Enum(WorkType), nullable=False, default=WorkType.BOOK)

    # series_id = Column(ForeignKey("series.id", name="fk_works_series_id"), nullable=True)

    # TODO may want to look at a TSVector GIN index for decent full text search
    title = Column(String(512), nullable=False, index=True)
    subtitle = Column(String(512), nullable=True)
    leading_article = Column(String(20), nullable=True)

    # TODO computed columns for display_title / sort_title

    info = Column(MutableDict.as_mutable(JSON))

    editions = relationship("Edition", cascade="all, delete-orphan")

    series = relationship(
        "Series", secondary=series_works_association_table, back_populates="works"
    )

    booklists = relationship(
        "BookList", secondary=booklist_work_association_table, back_populates="works"
    )

    # TODO edition count

    # Handle Multiple Authors via a secondary association table
    authors = relationship(
        "Author",
        secondary=author_work_association_table,
        back_populates="books",
        # https://docs.sqlalchemy.org/en/14/orm/loading_relationships.html#selectin-eager-loading
        lazy="selectin",
    )

    labelset = relationship(
        "LabelSet",
        uselist=False,
        back_populates="work",
        # lazy="joined"
    )

    def __repr__(self):
        return f"<Work id={self.id} - '{self.title}'>"
