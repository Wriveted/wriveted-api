from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Computed,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
    select,
)
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import column_property, relationship
from sqlalchemy.sql.functions import coalesce

from app.db import Base
from app.models.collection_item import CollectionItem
from app.models.illustrator_edition_association import (
    illustrator_edition_association_table,
)
from app.models.work import Work


class Edition(Base):
    id = Column(Integer, primary_key=True, autoincrement=True)

    isbn = Column(String(200), nullable=False, index=True, unique=True)

    work_id = Column(
        Integer,
        ForeignKey("works.id", name="fk_editions_works"),
        index=True,
        nullable=True,
    )
    work = relationship("Work", back_populates="editions", lazy="joined")

    # this might be a localized title
    edition_title = Column(String(512), nullable=True)
    edition_subtitle = Column(String(512), nullable=True)
    leading_article = Column(String(20), nullable=True)

    # TODO computed columns for display_title / sort_title based on the above

    title = column_property(
        select(coalesce(edition_title, Work.title))
        .where(Work.id == work_id)
        .correlate_except(Work)
        .scalar_subquery()
    )

    date_published = Column(Integer, nullable=True)

    cover_url = Column(String(200), nullable=True)

    # Info contains stuff like edition number, language
    # media (paperback/hardback/audiobook), number of pages.
    info = Column(MutableDict.as_mutable(JSON))

    # Proxy the authors from the related work
    authors = association_proxy("work", "authors")

    hydrated_at = Column(DateTime, nullable=True)
    hydrated = Column(
        Boolean,
        Computed("hydrated_at is not null"),
        index=True,
    )

    illustrators = relationship(
        "Illustrator",
        secondary=illustrator_edition_association_table,
        back_populates="editions",
        lazy="subquery",
    )

    collections = relationship(
        "Collection",
        secondary=CollectionItem.__table__,
        back_populates="items",
        lazy="selectin",
    )
    collection_count = column_property(
        select(func.count(CollectionItem.id))
        .where(CollectionItem.edition_isbn == isbn)
        .correlate_except(CollectionItem)
        .scalar_subquery()
    )

    def get_display_title(self) -> str:
        return (
            f"{self.leading_article} {self.edition_title}"
            if self.leading_article is not None
            else self.title
        )

    # ---------these are used for the hybrid attribute used in querying by number of collections in GET:editions/to_hydrate---------
    # https://docs.sqlalchemy.org/en/14/orm/extensions/hybrid.html#defining-expression-behavior-distinct-from-attribute-behavior

    # this method and its equivalent expression need the same method name to work
    @hybrid_property
    def num_collections(self):
        return self.collections.count()

    @num_collections.expression
    def num_collections(self):
        return (
            select(
                [
                    func.count(CollectionItem.__table__.c.edition_isbn).label(
                        "num_collections"
                    )
                ]
            )
            .where(CollectionItem.__table__.c.edition_isbn == self.isbn)
            .label("total_collections")
        )

    # -------------------------------------------------------------------------------------------------------------------------

    def __repr__(self):
        return f"<Edition '{self.isbn}', {self.get_display_title()}>"
