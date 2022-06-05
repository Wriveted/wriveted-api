from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import relationship

from app.db import Base


class BookListItem(Base):

    __tablename__ = "book_list_works"

    booklist_id = Column(
        ForeignKey(
            "book_lists.id", name="fk_booklist_items_booklist_id", ondelete="CASCADE"
        ),
        primary_key=True,
    )

    work_id = Column(
        ForeignKey("works.id", name="fk_booklist_items_work_id", ondelete="CASCADE"),
        primary_key=True,
    )

    created_at = Column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    order_id = Column(Integer)

    # Might need to opt in to say this is "deferrable"

    # Information about this particular work in the context of this list
    # E.g. "note": "Recommended by Alistair", "edition": "<isbn>"
    info = Column(MutableDict.as_mutable(JSON))

    booklist = relationship("BookList", back_populates="items")
    work = relationship("Work", lazy="joined", viewonly=True)

    __table_args__ = (
        Index("index_booklist_ordered", booklist_id, order_id),
        UniqueConstraint(
            "booklist_id", "order_id", name="ck_booklist_order", deferrable=True
        ),
    )

    def __repr__(self):
        try:
            return f"<BookListItem '{self.work.title}' @ '{self.booklist.name}'>"
        except AttributeError:
            return f"<BookListItem work_id={self.work_id}>"
