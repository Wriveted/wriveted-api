import enum
from sqlalchemy import (
    Column,
    Integer,
    String,
    JSON,
    select,
    func,
    and_,
    ForeignKey,
    Enum,
    DateTime,
)
from sqlalchemy.orm import relationship, column_property
from sqlalchemy.ext.mutable import MutableDict
from app.db import Base
from app.models.booklist_work_association import booklist_work_association_table
from app.models.work import Work


class ListType(str, enum.Enum):
    WISH_LIST = "Personal WishList"
    HAS_READ = "Personal Has-Read List"
    SCHOOL = "School Recommended"
    REGION_LIST = "Public State/Country List"
    HUEY_LIST = "HueyPicks List"
    OTHER_LIST = "Other List"


class BookList(Base):
    __tablename__ = "book_lists"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, index=True)
    type = Column(Enum(ListType), nullable=False)
    info = Column(MutableDict.as_mutable(JSON))
    created_at = Column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    works = relationship(
        "Work", secondary=booklist_work_association_table, back_populates="booklists"
    )

    school_id = Column(
        ForeignKey("schools.id", name="fk_booklist_school"), nullable=True
    )
    school = relationship(
        "School", back_populates="booklists", foreign_keys=[school_id]
    )

    user_id = Column(ForeignKey("users.id", name="fk_booklist_user"), nullable=True)
    user = relationship("User", back_populates="booklists", foreign_keys=[user_id])

    service_account_id = Column(
        ForeignKey("service_accounts.id", name="fk_booklist_service_account"),
        nullable=True,
    )
    service_account = relationship(
        "ServiceAccount", back_populates="booklists", foreign_keys=[service_account_id]
    )

    # Ref https://docs.sqlalchemy.org/en/14/orm/mapped_sql_expr.html#using-column-property
    book_count = column_property(
        select(func.count(Work.id))
        .where(
            and_(
                booklist_work_association_table.c.booklist_id == id,
                booklist_work_association_table.c.work_id == Work.id,
            )
        )
        .scalar_subquery()
    )

    def __repr__(self):
        return f"<Author id={self.id} - '{self.full_name}'>"
