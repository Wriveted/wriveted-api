import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    String,
    func,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import column_property, relationship

from app.db import Base
from app.models.booklist_work_association import BookListItem


class GroupType(str, enum.Enum):
    CLASS = "Class"
    CLUB = "Club"
    OTHER = "Other"


class UserGroup(Base):

    __tablename__ = "user_groups"

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

    group_type = Column(
        Enum(GroupType, name="enum_user_group_type"), nullable=False, index=True
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

    users = relationship(
        "UserGroupMembership",
        lazy="dynamic",
        cascade="all, delete, delete-orphan",
        passive_deletes=True,
        back_populates="user_group",
        order_by="asc(User.name)",
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
        return f"<UserGroup '{self.name}' type={self.type} id={self.id}>"
