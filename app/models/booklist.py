import enum
import uuid
from datetime import datetime

from fastapi_permissions import Allow, Authenticated, All
from sqlalchemy import (
    Column,
    String,
    JSON,
    select,
    func,
    ForeignKey,
    Enum,
    DateTime,
    text,
)

from sqlalchemy.orm import relationship, column_property
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.dialects.postgresql import UUID
from app.db import Base
from app.models.booklist_work_association import BookListItem


class ListType(str, enum.Enum):
    PERSONAL = "Personal"
    SCHOOL = "School"
    REGION = "Regional"
    HUEY = "Huey"
    OTHER_LIST = "Other"


class BookList(Base):

    __tablename__ = "book_lists"

    id = Column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        unique=True,
        primary_key=True,
        index=True,
        nullable=False,
    )

    name = Column(String(200), nullable=False, index=True)
    type = Column(
        Enum(ListType, name="enum_book_list_type"), nullable=False, index=True
    )
    info = Column(MutableDict.as_mutable(JSON))
    created_at = Column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    items = relationship(
        "BookListItem",
        lazy="dynamic",
        cascade="all, delete, delete-orphan",
        passive_deletes=True,
        back_populates="booklist",
        order_by="asc(BookListItem.order_id)",
    )

    book_count = column_property(
        select(func.count(BookListItem.work_id))
        .where(BookListItem.booklist_id == id)
        .correlate_except(BookListItem)
        .scalar_subquery()
    )

    works = relationship("Work", secondary=BookListItem.__tablename__, viewonly=True)

    school_id = Column(
        ForeignKey("schools.id", name="fk_booklist_school", ondelete="CASCADE"),
        nullable=True,
    )
    school = relationship(
        "School", back_populates="booklists", foreign_keys=[school_id]
    )

    user_id = Column(
        ForeignKey("users.id", name="fk_booklist_user", ondelete="CASCADE"),
        nullable=True,
    )
    user = relationship("User", back_populates="booklists", foreign_keys=[user_id])

    service_account_id = Column(
        ForeignKey(
            "service_accounts.id",
            name="fk_booklist_service_account",
            ondelete="CASCADE",
        ),
        nullable=True,
    )
    service_account = relationship(
        "ServiceAccount", back_populates="booklists", foreign_keys=[service_account_id]
    )

    def __repr__(self):
        return f"<BookList '{self.name}'  type={self.type} id={self.id}>"

    def __acl__(self):
        """
        Defines who can do what to the BookList instance.
        """

        policies = [
            (Allow, "role:admin", All),
            # Allow users to manage their own lists
            (Allow, f"user:{self.user_id}", All),
            # School admins can manage school lists
            (Allow, f"school:{self.school_id}", All),
        ]

        if self.type in {ListType.HUEY, ListType.REGION}:
            # Allow anyone Authenticated to view this "Public" book list
            policies.append(
                (Allow, Authenticated, "read")
            )

        return policies
