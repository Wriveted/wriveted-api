from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import Computed, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.series_works_association import series_works_association_table

if TYPE_CHECKING:
    from app.models.work import Work


class Series(Base):
    __tablename__ = "series"  # type: ignore[assignment]

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    title: Mapped[str] = mapped_column(String(512), nullable=False, unique=True, index=True)

    # make lowercase, remove "the " and "a " from the start, remove all non alphanumerics including whitespace.
    # The Chronicles of Narnia  = chroniclesofnarnia
    # CHRONICLES OF NARNIA      = chroniclesofnarnia
    # A Rather Cool Book Series = rathercoolbookseries
    # Not 100% perfect, but should catch the majority
    title_key: Mapped[str] = mapped_column(
        String(512),
        Computed(
            "LOWER(REGEXP_REPLACE(LOWER(title), '(^(\\w*the ))|(^(\\w*a ))|[^a-z0-9]', '', 'g'))"
        ),
        unique=True,
        index=True,
    )

    # author_id = mapped_column(
    #     Integer,
    #     ForeignKey("authors.id", name="fk_authors_series"),
    #     index=True,
    #     nullable=False
    # )
    # author = relationship('Author', back_populates='series', lazy='selectin')

    # description etc
    info: Mapped[Optional[Dict[str, Any]]] = mapped_column(MutableDict.as_mutable(JSONB))  # type: ignore[arg-type]

    # TODO order this relationship by the secondary table
    works: Mapped[List["Work"]] = relationship(
        "Work", secondary=series_works_association_table, back_populates="series"
    )

    def __repr__(self) -> str:
        return f"<Series id={self.id} - '{self.title}'>"
