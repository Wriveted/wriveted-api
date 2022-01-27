from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
    JSON,
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.mutable import MutableDict
from app.db import Base
from app.models.series_works_association import series_works_association_table


class Series(Base):

    id = Column(Integer, primary_key=True, autoincrement=True)

    title = Column(String(512), nullable=False, unique=True, index=True)

    # author_id = Column(
    #     Integer,
    #     ForeignKey("authors.id", name="fk_authors_series"),
    #     index=True,
    #     nullable=False
    # )
    # author = relationship('Author', back_populates='series', lazy='selectin')

    # description etc
    info = Column(MutableDict.as_mutable(JSON))

    # TODO order this relationship by the secondary table
    works = relationship(
        'Work',
        secondary=series_works_association_table,
        back_populates="series"
    )
