from sqlalchemy import (
    Column,
    Computed,
    Integer,
    String,
    JSON,
    select,
    func,
    and_,
)
from sqlalchemy.orm import relationship, column_property
from sqlalchemy.ext.mutable import MutableDict
from app.db import Base
from app.models.author_work_association import author_work_association_table
from app.models.work import Work


class Author(Base):
    id = Column(Integer, primary_key=True, autoincrement=True)

    first_name = Column(String(200), nullable=False, index=True)
    last_name = Column(String(200), nullable=False, index=True)

    # Building on the assumption of unique full names, an author's full name (sans whitespace and punctuation)
    # can serve as a unique key that can be caught even if data differs slightly (C.S. Lewis vs C S Lewis)
    name_key = Column(
        String(400),
        Computed("LOWER(REGEXP_REPLACE(first_name || last_name, '\\W|_', '', 'g'))"),
        unique=True,
        index=True,
    )

    info = Column(MutableDict.as_mutable(JSON))

    books = relationship(
        "Work",
        secondary=author_work_association_table,
        back_populates="authors"
        # cascade="all, delete-orphan"
    )

    # series = relationship('Series', cascade="all")

    # Ref https://docs.sqlalchemy.org/en/14/orm/mapped_sql_expr.html#using-column-property
    book_count = column_property(
        select(func.count(Work.id))
        .where(
            and_(
                author_work_association_table.c.author_id == id,
                author_work_association_table.c.work_id == Work.id,
            )
        )
        .scalar_subquery()
    )

    def __repr__(self):
        return f"<Author id={self.id} - '{self.first_name} {self.last_name} '>"
