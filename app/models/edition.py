from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, JSON, func, select
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import backref
from sqlalchemy.orm import relationship, column_property
from sqlalchemy.sql.functions import coalesce

from app.db import Base
from app.models.collection_item import CollectionItem
from app.models.work import Work
from app.models.illustrator_edition_association import (
    illustrator_edition_association_table,
)


class Edition(Base):
    id = Column(Integer, primary_key=True, autoincrement=True)

    isbn = Column(String(200), nullable=False, index=True, unique=True)

    work_id = Column(
        Integer,
        ForeignKey("works.id", name="fk_editions_works"),
        index=True,
        nullable=True
    )
    work = relationship("Work", back_populates="editions", lazy="selectin")

    # this might be a localized title
    edition_title = Column(String(512), nullable=True)

    title = column_property(
        select(coalesce(edition_title, Work.title))
        .where(Work.id == work_id)
        .correlate_except(Work)
        .scalar_subquery()
    )

    cover_url = Column(String(200), nullable=True)

    # Info contains stuff like edition number, language
    # Published date, published by, media (paperback/hardback/audiobook),
    # number of pages.
    info = Column(MutableDict.as_mutable(JSON))

    # Proxy the authors from the related work
    authors = association_proxy("work", "authors")

    hydrated = Column(Boolean(), default=False)

    illustrators = relationship(
        "Illustrator",
        secondary=illustrator_edition_association_table,
        back_populates="editions",
        lazy="subquery",
    )

    schools = relationship(
        'School', 
        secondary=CollectionItem.__table__,
        backref = backref('editions', lazy='dynamic')
    )

    school_count = column_property(
        select(func.count(CollectionItem.id))
        .where(CollectionItem.edition_isbn == isbn)
        .correlate_except(CollectionItem)
        .scalar_subquery()
    )

    # this method and its equivalent expression need the same method name to work
    @hybrid_property
    def num_schools(self):
        return self.schools.count()

    # these are used for the hybrid attribute used in querying by number of schools
    # https://docs.sqlalchemy.org/en/14/orm/extensions/hybrid.html#defining-expression-behavior-distinct-from-attribute-behavior
    @num_schools.expression
    def num_schools(self):
        return (select([func.count(CollectionItem.__table__.c.edition_isbn).label("num_schools")])
                .where(CollectionItem.__table__.c.edition_isbn == self.isbn)
                .label("total_schools")
                )


    def __repr__(self):
        return f"<Edition '{self.title}'>"
