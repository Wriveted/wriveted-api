from sqlalchemy import Column, ForeignKey, Integer, String, JSON, Computed
from sqlalchemy.orm import relationship
from sqlalchemy.ext.mutable import MutableDict
from app.db import Base
from app.models.series_works_association import series_works_association_table


class Series(Base):

    id = Column(Integer, primary_key=True, autoincrement=True)

    title = Column(String(512), nullable=False, unique=True, index=True)

    # make lowercase, remove "the " and "a " from the start, remove all non alphanumerics including whitespace.
    # The Chronicles of Narnia  = chroniclesofnarnia
    # CHRONICLES OF NARNIA      = chroniclesofnarnia
    # A Rather Cool Book Series = rathercoolbookseries
    # Not 100% perfect, but should catch the majority
    title_key = Column(
        String(512),
        Computed(
            "LOWER(REGEXP_REPLACE(LOWER(title), '(^(\\w*the ))|(^(\\w*a ))|[^a-z0-9]', '', 'g'))"
        ),
        unique=True,
        index=True,
    )

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
        "Work", secondary=series_works_association_table, back_populates="series"
    )
