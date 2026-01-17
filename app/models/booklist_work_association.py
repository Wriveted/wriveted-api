from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.booklist import BookList
    from app.models.work import Work


class BookListItem(Base):
    __tablename__ = "book_list_works"  # type: ignore[assignment]

    booklist_id: Mapped[int] = mapped_column(
        ForeignKey(
            "book_lists.id", name="fk_booklist_items_booklist_id", ondelete="CASCADE"
        ),
        primary_key=True,
    )

    work_id: Mapped[int] = mapped_column(
        ForeignKey("works.id", name="fk_booklist_items_work_id", ondelete="CASCADE"),
        primary_key=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    order_id: Mapped[Optional[int]] = mapped_column(Integer)

    # Might need to opt in to say this is "deferrable"

    # Information about this particular work in the context of this list
    # E.g. "note": "Recommended by Alistair", "edition": "<isbn>"
    info: Mapped[Optional[Dict[str, Any]]] = mapped_column(MutableDict.as_mutable(JSON))  # type: ignore[arg-type]

    booklist: Mapped["BookList"] = relationship("BookList", back_populates="items")
    work: Mapped["Work"] = relationship("Work", lazy="joined", viewonly=True)

    __table_args__ = (
        Index(
            "ix_booklistworkassociations_booklist_id_order_id", booklist_id, order_id
        ),
        UniqueConstraint(
            "booklist_id",
            "order_id",
            name="uq_booklistworkassociations_booklist_id_order_id",
            deferrable=True,
        ),
    )

    def __repr__(self) -> str:
        try:
            return f"<BookListItem '{self.work.title}' @ '{self.booklist.name}'>"
        except AttributeError:
            return f"<BookListItem work_id={self.work_id}>"
