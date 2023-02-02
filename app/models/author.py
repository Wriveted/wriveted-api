from sqlalchemy import JSON, Computed, Integer, String, and_, func, select
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, column_property, mapped_column, relationship

from app.db import Base
from app.models.author_work_association import author_work_association_table
from app.models.work import Work


class Author(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    first_name: Mapped[str] = mapped_column(String(200), nullable=True, index=True)
    last_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)

    # Building on the assumption of unique full names, an author's full name (sans whitespace and punctuation)
    # can serve as a unique key that can be caught even if data differs slightly (C.S. Lewis vs C S Lewis)
    name_key: Mapped[str] = mapped_column(
        String(400),
        Computed("LOWER(REGEXP_REPLACE(first_name || last_name, '\\W|_', '', 'g'))"),
        unique=True,
        index=True,
    )

    # TODO check if can we get better typed JSON/dicts
    info: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON))

    books: Mapped["Work"] = relationship(
        "Work", secondary=author_work_association_table, back_populates="authors"
    )

    # series = relationship('Series', cascade="all")

    # Ref https://docs.sqlalchemy.org/en/14/orm/mapped_sql_expr.html#using-column-property
    book_count: Mapped[int] = column_property(
        select(func.count(Work.id))
        .where(
            and_(
                author_work_association_table.c.author_id == id,
                author_work_association_table.c.work_id == Work.id,
            )
        )
        .scalar_subquery(),
        deferred=True,
    )

    def __repr__(self):
        return f"<Author id={self.id} - '{self.first_name} {self.last_name} '>"

    def __str__(self):
        if self.first_name is not None:
            return f"{self.first_name} {self.last_name}"
        else:
            return self.last_name
