from sqlalchemy import JSON, Enum, Integer, String, desc, nulls_last, select
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.db.common_types import intpk
from app.models.author_work_association import author_work_association_table
from app.models.booklist_work_association import BookListItem
from app.models.edition import Edition
from app.models.series_works_association import series_works_association_table
from app.schemas import CaseInsensitiveStringEnum


class WorkType(CaseInsensitiveStringEnum):
    BOOK = "book"
    PODCAST = "podcast"


class Work(Base):

    id: Mapped[intpk] = mapped_column(Integer, primary_key=True, autoincrement=True)

    type = mapped_column(Enum(WorkType), nullable=False, default=WorkType.BOOK)

    # series_id = mapped_column(ForeignKey("series.id", name="fk_works_series_id"), nullable=True)

    # TODO may want to look at a TSVector GIN index for decent full text search
    title = mapped_column(String(512), nullable=False, index=True)
    subtitle = mapped_column(String(512), nullable=True)
    leading_article = mapped_column(String(20), nullable=True)

    # TODO computed columns for display_title / sort_title

    info = mapped_column(MutableDict.as_mutable(JSON))

    editions = relationship(
        "Edition",
        cascade="all, delete-orphan",
        order_by="desc(Edition.cover_url.is_not(None))",
    )

    series = relationship(
        "Series", secondary=series_works_association_table, back_populates="works"
    )

    booklists = relationship(
        "BookList",
        secondary=BookListItem.__tablename__,
        back_populates="works",
        viewonly=True,
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

    def get_display_title(self) -> str:
        return (
            f"{self.leading_article} {self.title}"
            if self.leading_article is not None
            else self.title
        )

    def get_feature_edition(self, session):
        """
        Get the best edition to feature for this work.
        Looks for cover images first, then falls back to the most recent edition.
        """
        return session.scalars(
            select(Edition)
            .where(Edition.work_id == self.id)
            .order_by(
                nulls_last(desc(Edition.cover_url)), Edition.date_published.desc()
            )
            .limit(1)
        ).first()

    def get_authors_string(self):
        return ", ".join(map(str, self.authors))

    def __repr__(self):
        return f"<Work id={self.id} - '{self.title}'>"
