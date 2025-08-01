from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import Enum, Integer, String, desc, nulls_last, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.db.common_types import intpk
from app.models.author_work_association import author_work_association_table
from app.models.booklist_work_association import BookListItem
from app.models.series_works_association import series_works_association_table
from app.schemas import CaseInsensitiveStringEnum

if TYPE_CHECKING:
    from app.models.author import Author
    from app.models.booklist import BookList
    from app.models.edition import Edition
    from app.models.labelset import LabelSet
    from app.models.series import Series


class WorkType(CaseInsensitiveStringEnum):
    BOOK = "book"
    PODCAST = "podcast"


class Work(Base):
    __tablename__ = "works"  # type: ignore[assignment]

    id: Mapped[intpk] = mapped_column(Integer, primary_key=True, autoincrement=True)

    type: Mapped[WorkType] = mapped_column(Enum(WorkType), nullable=False, default=WorkType.BOOK)

    # series_id = mapped_column(ForeignKey("series.id", name="fk_works_series_id"), nullable=True)

    # TODO may want to look at a TSVector GIN index for decent full text search
    title: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    subtitle: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    leading_article: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # TODO computed columns for display_title / sort_title

    info: Mapped[Optional[Dict[str, Any]]] = mapped_column(MutableDict.as_mutable(JSONB))  # type: ignore[arg-type]

    editions: Mapped[List["Edition"]] = relationship(
        "Edition",
        cascade="all, delete-orphan",
        order_by="desc(Edition.cover_url.is_not(None))",
    )

    series: Mapped[List["Series"]] = relationship(
        "Series", secondary=series_works_association_table, back_populates="works"
    )

    booklists: Mapped[List["BookList"]] = relationship(
        "BookList",
        secondary=BookListItem.__tablename__,
        back_populates="works",
        viewonly=True,
    )

    # TODO edition count

    # Handle Multiple Authors via a secondary association table
    authors: Mapped[List["Author"]] = relationship(
        "Author",
        secondary=author_work_association_table,
        back_populates="books",
        # https://docs.sqlalchemy.org/en/14/orm/loading_relationships.html#selectin-eager-loading
        lazy="selectin",
    )

    labelset: Mapped[Optional["LabelSet"]] = relationship(
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

    def get_feature_edition(self, session: Any) -> Optional["Edition"]:
        """
        Get the best edition to feature for this work.
        Looks for cover images first, then falls back to the most recent edition.
        """
        from app.models.edition import Edition
        
        result = session.scalars(
            select(Edition)
            .where(Edition.work_id == self.id)
            .order_by(
                nulls_last(desc(Edition.cover_url)), Edition.date_published.desc()
            )
            .limit(1)
        ).first()
        return result  # type: ignore[no-any-return]

    def get_authors_string(self) -> str:
        return ", ".join(map(str, self.authors))

    def __repr__(self) -> str:
        return f"<Work id={self.id} - '{self.title}'>"

    def get_dict(self, session: Any) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "leading_article": self.leading_article,
            "title": self.title,
            "subtitle": self.subtitle,
            "authors": [
                {
                    "id": author.id,
                    "first_name": author.first_name,
                    "last_name": author.last_name,
                }
                for author in self.authors
            ],
            "labelset": (
                self.labelset.get_label_dict(session) if self.labelset else None
            ),
        }
