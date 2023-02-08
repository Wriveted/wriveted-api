import enum
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi_permissions import All, Allow, Authenticated
from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, func, select, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, column_property, mapped_column, relationship

from app.db import Base
from app.models.booklist_work_association import BookListItem


class ListType(str, enum.Enum):
    PERSONAL = "Personal"
    SCHOOL = "School"
    REGION = "Regional"
    HUEY = "Huey"
    OTHER_LIST = "Other"


class ListSharingOptions(str, enum.Enum):
    PRIVATE = "private"
    RESTRICTED = "restricted"  # Some other mechanism will determine who can view..
    PUBLIC = "public"


class BookList(Base):

    __tablename__ = "book_lists"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        unique=True,
        primary_key=True,
        index=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    type: Mapped[ListType] = mapped_column(
        Enum(ListType, name="enum_book_list_type"), nullable=False, index=True
    )
    # sharing = mapped_column(
    #     Enum(ListSharingOptions, name="enum_book_list_sharing"), nullable=False, index=True,
    #     default=ListSharingOptions.PRIVATE
    # )

    info: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSON))

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    items: Mapped[List["BookListItem"]] = relationship(
        "BookListItem",
        lazy="dynamic",
        cascade="all, delete, delete-orphan",
        passive_deletes=True,
        back_populates="booklist",
        order_by="asc(BookListItem.order_id)",
    )

    book_count: Mapped[int] = column_property(
        select(func.count(BookListItem.work_id))
        .where(BookListItem.booklist_id == id)
        .correlate_except(BookListItem)
        .scalar_subquery()
    )

    works: Mapped[List["Work"]] = relationship(
        "Work", secondary=BookListItem.__tablename__, viewonly=True
    )

    school_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("schools.id", name="fk_booklist_school", ondelete="CASCADE"),
        nullable=True,
    )

    school: Mapped[Optional["School"]] = relationship(
        "School", back_populates="booklists", foreign_keys=[school_id]
    )

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", name="fk_booklist_user", ondelete="CASCADE"),
        nullable=True,
    )
    user: Mapped[Optional["User"]] = relationship(
        "User", back_populates="booklists", foreign_keys=[user_id], lazy="joined"
    )

    service_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "service_accounts.id",
            name="fk_booklist_service_account",
            ondelete="CASCADE",
        ),
        nullable=True,
    )
    service_account: Mapped["ServiceAccount"] = relationship(
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
            # Allow users (or their parents) to manage their own lists
            (Allow, f"user:{self.user_id}", All),
            (Allow, f"parent:{self.user_id}", All),
            # Educators can manage school lists
            (Allow, f"educator:{self.school_id}", All),
            (Allow, f"school:{self.school_id}", All),
        ]

        if self.type in {ListType.HUEY, ListType.REGION}:
            # Allow anyone Authenticated to view this "Public" book list
            policies.append((Allow, Authenticated, "read"))

        if self.type == ListType.SCHOOL:
            # Allow students to view all School lists
            policies.append(((Allow, f"student:{self.school_id}", "read")))

        return policies
